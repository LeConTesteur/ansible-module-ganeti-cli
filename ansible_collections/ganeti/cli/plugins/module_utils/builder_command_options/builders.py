import copy
import datetime
from functools import reduce, wraps
from itertools import chain, repeat, zip_longest
import re
import abc
from typing import Any, Dict, Iterator, List, Union, Callable
from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options.builder_functions import build_options_with_prefixes, build_prefixes_from_count_diff, build_single_option, build_sub_dict_options
from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options.extractors import ValueInfoExtractor, ValueParamExtractor, recursive_get, size_param_info_extractor, value_info_extractor


from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options.prefixes import (
    Prefix, PrefixAdd, PrefixModify, PrefixNone, PrefixRemove, PrefixTypeEnum, format_prefix)

class DefaultValue:
    def __init__(self, value) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

DEFAULT_VALUE = DefaultValue('default')
NONE_VALUE = DefaultValue('None')

IGNORE_INFO_KEY = object()



PrefixBuilder = Callable[[Any, Any], Prefix]


class BuilderCommandOptionsSpecAbstract:
    def __init__(self, *, parent = None, name:str, info_key:str=None, param_extractor:ValueParamExtractor=recursive_get, info_extractor:ValueInfoExtractor=value_info_extractor) -> None:
        self._name = name
        self._info_key = info_key
        self.parent = parent
        self._param_extractor = param_extractor
        self._info_extractor = info_extractor
    
    def __repr__(self) -> str:
        return 'Spec: {} -> {}'.format(self._name, self._info_key)
    
    def recurive(property_name:str):
        def decorator(func):
            @wraps(func)
            def wrapper(self) -> Iterator[str]:
                it = [getattr(self, property_name)]
                if self.parent is None:
                    return it
                return filter(lambda x:x, chain(getattr(self.parent, func.__name__)(), it))
            return wrapper
        return decorator
    
    @property
    def name(self):
        return self._name

    @recurive('name')
    def names(self) -> Iterator[str]:
        pass

    @property
    def info_key(self) -> str:
        if self._info_key == IGNORE_INFO_KEY:
            return None
        return self._info_key or self.name

    @recurive('info_key')
    def info_keys(self) -> Iterator[str]:
        pass

    @abc.abstractmethod
    def to_args_spec(self) -> Dict:
        pass

    @abc.abstractmethod
    def to_options(self, ansible_param, info) -> Iterator[str]:
        pass

class BuilderCommandOptionsSpec(BuilderCommandOptionsSpecAbstract):
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract], **kwargs) -> None:
        super().__init__(**kwargs)
        self._spec = args
        for _spec in self._spec:
            _spec.parent = self
            

    def to_args_spec(self) -> Dict:
        return {
            spec.name: spec.to_args_spec() for spec in self._spec
        }

    def to_options(self, ansible_param, info) -> Iterator[str]:
        return chain(*[spec.to_options(ansible_param, info) for spec in self._spec])

class BuilderCommandOptionsRootSpec(BuilderCommandOptionsSpec):
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract]) -> None:
        super().__init__(*args, name='params', info_key=IGNORE_INFO_KEY)


class BuilderCommandOptionsSpecDict(BuilderCommandOptionsSpec):
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract], prefix_builder: PrefixBuilder = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.prefix_builder = prefix_builder

    def to_args_spec(self) -> Dict:
        return {
            'type': 'dict',
            'required': False,
            'options': super().to_args_spec(),
        }

    def to_options(self, ansible_param, info) -> List[str]:
        prefix = PrefixNone()
        if self.prefix_builder is not None:
            prefix = self.prefix_builder(ansible_param, info)
        option = ','.join(chain.from_iterable([spec.to_options(ansible_param, info) for spec in self._spec]))
        return [ build_options_with_prefixes(
                [option] if option else [],
                option_name=self.name,
                prefixes=prefix
        )]

class BuilderCommandOptionsSpecList(BuilderCommandOptionsSpec):
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract], no_option:str = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.no_option = no_option
    def to_args_spec(self) -> Dict:
        return {
            'type': 'list',
            'required': False,
            'options': super().to_args_spec(),
        }

    def to_options(self, ansible_param, info) -> Iterator[str]:
        param_value = self._param_extractor(ansible_param, self.names()) or []
        info_value = self._info_extractor(info, self.info_keys()) or []
        size_param_list, size_info_list = len(param_value), len(info_value)
        value = []
        if size_param_list == 0 and self.no_option:
            value.append(self.no_option)
        prefixes = list(build_prefixes_from_count_diff(size_param_list, size_info_list))
        value.append(
            build_options_with_prefixes(
                chain.from_iterable([
                    _BuilderCommandOptionsSpecListElement(*self._spec, index=index)
                        .to_options(value[0], value[1])
                    for index, value in enumerate(zip_longest(param_value, info_value, fillvalue={}))
                ]), 
                self.name,
                prefixes=prefixes
                )
        )
        return value
        

class _BuilderCommandOptionsSpecListElement(BuilderCommandOptionsSpecAbstract):
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract], index:int = None) -> None:
        super().__init__(parent=None, name=None, info_key=None)
        self._spec = copy.deepcopy(args)
        for spec in self._spec:
            spec.parent = self
            spec.set_index(index)
        

    def to_options(self, ansible_param, info) -> Iterator[str]:
        return [ ','.join(chain.from_iterable([spec.to_options(ansible_param, info) for spec in self._spec])) ]
        

class BuilderCommandOptionsSpecElement(BuilderCommandOptionsSpecAbstract):
    def __init__(self, *, type:str, required:bool=False, default: Any = None, default_ganeti:str=DEFAULT_VALUE, build_function=build_single_option, **kwargs) -> None:
        super().__init__(**kwargs)
        self.type = type
        self.required = required
        self.default = default
        self.default_ganeti = default_ganeti
        self.build_function = build_function

    def to_args_spec(self) -> Dict:
        return {
            'type': self.type,
            'required': self.required,
            'default': self.default
        }
    
    def to_options(self, ansible_param, info) -> Iterator[str]:
        param_value = self._param_extractor(ansible_param, self.names())
        info_value = self._info_extractor(info, self.info_keys())
        if param_value == info_value:
            return []
        value = self.default_ganeti
        if param_value is not None and info_value != param_value:
            value = param_value
        return [self.build_function(self.name, value)]

class BuilderCommandOptionsSpecSubElement(BuilderCommandOptionsSpecElement):
    def __init__(self, *_, index:int = None, **kwargs) -> None:
        super().__init__(build_function=build_sub_dict_options,**kwargs)
        self.set_index(index)

    def __repr__(self) -> str:
        index = ''
        if hasattr(self, 'index'):
            index =  ' / {}'.format(self.index)
        return '{}{}'.format(super().__repr__(), index)

    def set_index(self, index:int):
        if index is not None:
            self.index = index

    @property
    def info_key(self) -> str:
        if hasattr(self, 'index'):
            return super().info_key.format(self.index)
        return super().info_key

class BuilderCommandOptionsSpecListSubElement(BuilderCommandOptionsSpecSubElement):
    def __init__(self, *_, default_ganeti=NONE_VALUE, **kwargs):
        super().__init__(default_ganeti=default_ganeti, **kwargs)

class BuilderCommand:
    def __init__(self, binary:str, spec:BuilderCommandOptionsSpec) -> None:
        self.binary:str = binary
        self.spec:BuilderCommandOptionsSpec = spec

    def generate_args_spec(self) -> Dict:
        return self.spec.to_args_spec()

    def generate(self, command:str, *extra_options:List[str], module_params: dict, info_data: dict) -> str:
        return ' '.join(
            filter(
                lambda x:x, 
                chain(
                    [self.binary, command],
                    extra_options,
                    self.spec.to_options(module_params, info_data)
                )
            )
        )
        


spec = BuilderCommandOptionsRootSpec(
    BuilderCommandOptionsSpecElement(name='disk_template', type='str'),
    BuilderCommandOptionsSpecList(
        BuilderCommandOptionsSpecListSubElement(name='name', type='str'),
        BuilderCommandOptionsSpecListSubElement(name='size', type='str', info_key='disk/{}', required=True, param_extractor=size_param_info_extractor, info_extractor=size_param_info_extractor),
        name="disks",
        info_key = 'Disks'
    ),
    BuilderCommandOptionsSpecDict(
        BuilderCommandOptionsSpecSubElement(name='memory', type='int'),
        BuilderCommandOptionsSpecSubElement(name='vcpus', type='int'),
        name='backend_param',
        info_key = 'Back-end parameters',
    )
)


# info = {'Instance name': 'test', 'UUID': '550fc540-dda2-4c11-95a0-6c1de852c11d', 'Serial number': 3, 'Creation time': datetime.datetime(2023, 2, 6, 21, 44, 56), 'Modification time': datetime.datetime(2023, 2, 6, 21, 44, 59), 'State': 'configured to be up, actual state is up', 'Nodes': [{'primary': 'node1', 'group': None}, {'secondaries': None}], 'Operating system': 'noop', 'Operating system parameters': None, 'Allocated network port': None, 'Hypervisor': 'fake', 'Hypervisor parameters': None, 'Back-end parameters': {'always_failover': None, 'auto_balance': None, 'maxmem': None, 'memory': None, 'minmem': None, 'spindle_use': None, 'vcpus': 4}, 'NICs': [{'nic/0': None, 'MAC': 'aa:00:00:6b:2b:d0', 'IP': None, 'mode': 'bridged', 'link': 'br_gnt', 'vlan': None, 'network': None, 'UUID': '1290a6d7-b6ee-4324-ba2c-57c9c3bb61c5', 'name': None}], 'Disk template': 'file', 'Disks': [{'disk/0': 'file, size 10.0G', 'access mode': 'rw', 'logical_id': ['loop', '/srv/ganeti/file-storage/test/8287dcbb-b8fe-4e0e-acdd-6ac909db01f6.file.disk0'], 'on primary': '/srv/ganeti/file-storage/test/8287dcbb-b8fe-4e0e-acdd-6ac909db01f6.file.disk0 (N/A:N/A)', 'name': None, 'UUID': '031b68c5-30b9-4ca4-bfc1-3259384335f1'}]}
# param = {"state": "present", "admin_state": "started", "reboot_if_change": False, "params": {"disks": [{"name": "disk0", "size": "10G"}, {"size":"12G"}], "pnode": None, "hypervisor": "kvm", "disk_template": "file", "backend_param": None, "nics": [{"mode": "bridged", "link": "br_gnt", "name": "test"}], "hypervisor_params": None, "name_check": False, "ip_check": False, "iallocator": None, "os_type": "noop"}, "name": "test"}
# print(spec.to_args_spec())
# print(list(spec.to_options(param,info)))
# print(BuilderCommand('gnt-instance',spec).generate('add', '--no-start', module_params=param, info_data=info))