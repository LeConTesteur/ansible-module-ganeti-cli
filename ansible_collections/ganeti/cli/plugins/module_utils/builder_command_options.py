import copy
import datetime
from functools import reduce
from itertools import chain, repeat, zip_longest
import re
import yaml
from typing import Any, Dict, Iterator, List, Union, Callable
from flatdict import FlatterDict
from collections import UserList

from ansible_collections.ganeti.cli.plugins.module_utils.command_options_prefix import Prefix, PrefixAdd, PrefixModify, PrefixNone, PrefixRemove, PrefixTypeEnum, format_prefix

class DefaultValue:
    def __init__(self, value) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

DEFAULT_VALUE = DefaultValue('default')
NONE_VALUE = DefaultValue('None')

IGNORE_INFO_KEY = object()

def dict_get(data:dict, key:str):
    if data is None:
        return None
    return dict.get(data, key)


def recursive_get(data: dict, keys:List[str]) -> Any:
    return reduce(dict_get, keys, data)

def value_info_extractor(data:dict, keys:List[str]) -> Any:
    value = recursive_get(data, keys)
    if not isinstance(value, str):
        return value
    return yaml.safe_load(value)

def size_param_info_extractor(data:dict, keys:List[str]) -> Any:
    value = recursive_get(data, keys)
    if not value:
        return None
    match = re.search(r'(?P<value>[.0-9]+)(?P<unit>[a-zA-Z])', value)
    if not match:
        return None
    return '{}{}'.format(float(match.group('value')), match.group('unit'))
    
    

def build_prefixes_from_count_diff(expected_count:int, actual_count: int) -> Iterator:
    """Create list of Prefix depends of difference between expected and actual count

    Args:
        expected_count (int): The count expected in playbook
        actual_count (int): The acount actual in server

    Raises:
        Exception: If actual count is negative

    Returns:
        _type_: An iterator of Prefix

    Yields:
        Iterator: An iterator of Prefix
    """
    if expected_count <= 0:
        return iter([])

    if actual_count < 0:
        raise ValueError('Error in remote count')
    count_diff = expected_count - actual_count

    ret = []

    if count_diff == 0: # same number
        ret = repeat(PrefixModify(), expected_count)

    elif count_diff < 0: #Much element, need remove surplus
        ret = chain(
                repeat(PrefixModify(), expected_count),
                repeat(PrefixRemove(), abs(count_diff))
            )
    elif count_diff > 0: #Missing element, need add missing
        ret = chain(
                repeat(PrefixModify(), actual_count),
                repeat(PrefixAdd(), abs(count_diff))
            )
    return iter(ret)

def build_dict_options_with_prefix(
        options: List[str], option_name:str, prefixes: Union[List[Prefix], Prefix]=None) -> str:
    """
    Builder of options for add list options (like --net, --disk)
    """

    options = list(filter(lambda x: x, options)) #remove empty string

    if not options:
        return ""

    if not option_name:
        raise ValueError('Missing option_name')

    if not prefixes:
        prefixes = [PrefixNone()]

    return " ".join(
        [
            "--{option_name} {prefix}{options}".format(
                option_name=option_name,
                prefix=format_prefix(value[1], index),
                options=value[0] \
                        if value[1].type != PrefixTypeEnum.REMOVE else ''
            )
            for index, value in enumerate(zip_longest(options, prefixes, fillvalue=prefixes[-1]))
        ]
    )

def diff(first: FlatterDict, second: FlatterDict, delimiter='.'):
    summary = {
        'add': FlatterDict(delimiter=delimiter),
        'modify': FlatterDict(delimiter=delimiter),
        'remove': FlatterDict(delimiter=delimiter)
    }
    def key_have_list(key:str) -> bool:
        return re.match(r'[{d}]\d+([{d}]|$)'.format(d=delimiter), key) is not None
    def split_key_list(key:str, delimiter=delimiter) -> str:
        for index in range(10, 0,-1):
            match = re.match(r'(([{d}]?[a-zA-Z])+[{d}]\d+){{{i}}}'.format(d=delimiter, i=index), key)
            if match is None:
                continue
            yield match.group(0)
    for k_first, v_first in first.items():
        if k_first not in second:
            summary['add'][k_first] = v_first # append value
        elif second[k_first] != v_first:
            summary['modify'][k_first] = v_first # modify value or set to default
    for k_second in second.keys():
        key_to_remove = None
        if key_have_list(k_second):
            for key in split_key_list(k_second):
                if key not in first:
                    key_to_remove = key
        if key_to_remove is not None:
            summary['remove'][key_to_remove] = None
        elif k_second not in first and not key_have_list(k_second):
            summary['modify'][k_second] = DEFAULT_VALUE # set to default
        elif k_second not in first and key_have_list(k_second):
            summary['modify'][k_second] = NONE_VALUE # set to default
    return summary

def build_state_option(name:str, value:Any) -> str:
    """Build option string for one value

    Args:
        name (str): name of option
        value (Any): value of option

    Returns:
        str: the option
    """
    return "--no-{}".format(name) if value is not None and not value else ""

def build_single_option(name:str, value:Any) -> str:
    """Build option string for one value

    Args:
        name (str): name of option
        value (Any): value of option

    Returns:
        str: the option
    """
    return "--{}={}".format(name, value) if value is not None else ""

PrefixBuilder = Callable[[Any, Any], Prefix]
ValueParamExtractor = Callable[[Dict, List[str]], Any]
ValueInfoExtractor = Callable[[Dict, List[str]], Any]


class BuilderCommandOptionsSpecAbstract:
    def __init__(self, *, parent = None, name:str, info_key:str=None, delimiter:str='.', param_extractor:ValueParamExtractor=recursive_get, info_extractor:ValueInfoExtractor=value_info_extractor) -> None:
        self._name = name
        self._info_key = info_key
        self.parent = parent
        self._delimiter = delimiter
        self._param_extrator = param_extractor
        self._info_extrator = info_extractor
    
    @property
    def name(self):
        return self._name

    @property
    def names(self):
        it = [self.name] if self.name is not None else []
        if self.parent is None:
            return it
        return chain(self.parent.names, it)

    @property
    def absolute_info_key(self) -> str:
        return self._delimiter.join(self.info_keys)

    @property
    def info_key(self) -> str:
        if self._info_key == IGNORE_INFO_KEY:
            return None
        return self._info_key or self.name

    @property
    def info_keys(self) -> Iterator[str]:
        it = iter([self.info_key]) if self.info_key is not None else []
        if self.parent is None:
            return it
        return chain(self.parent.info_keys, it)

    def to_args_spec(self) -> Any:
        pass

class BuilderCommandOptionsSpec(BuilderCommandOptionsSpecAbstract):
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract], **kwargs) -> None:
        super().__init__(**kwargs)
        self._spec = args
        for _spec in self._spec:
            _spec.parent = self
            

    def to_args_spec(self) -> Any:
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

    def to_args_spec(self) -> Any:
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
        return [ build_dict_options_with_prefix(
                [option] if option else [],
                option_name=self.name,
                prefixes=prefix
        )]

class BuilderCommandOptionsSpecList(BuilderCommandOptionsSpec):
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract], no_option:str = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.no_option = no_option
    def to_args_spec(self) -> Any:
        return {
            'type': 'list',
            'required': False,
            'options': super().to_args_spec(),
        }

    def to_options(self, ansible_param, info) -> Iterator[str]:
        param_value = self._param_extrator(ansible_param, self.names) or []
        info_value = self._info_extrator(info, self.info_keys) or []
        size_param_list = len(param_value)
        size_info_list = len(info_value)
        value = []
        if size_param_list == 0 and self.no_option:
            value.append(self.no_option)
        prefixes = list(build_prefixes_from_count_diff(size_param_list, size_info_list))
        value.append(
            build_dict_options_with_prefix(
                chain.from_iterable([
                    _BuilderCommandOptionsSpecListElement(*self._spec, index=index, delimiter=self._delimiter)
                        .to_options(value[0], value[1])
                    for index, value in enumerate(zip_longest(param_value, info_value, fillvalue={}))
                ]), 
                self.name,
                prefixes=prefixes
                )
        )
        return value
        

class _BuilderCommandOptionsSpecListElement(BuilderCommandOptionsSpecAbstract):
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract], index:int = None,  delimiter: str = '.') -> None:
        super().__init__(parent=None, name=None, info_key=None, delimiter=delimiter)
        self._spec = copy.deepcopy(args)
        for spec in self._spec:
            spec.parent = self
            spec.set_index(index)
        

    def to_options(self, ansible_param, info) -> Iterator[str]:
        return [ ','.join(chain.from_iterable([spec.to_options(ansible_param, info) for spec in self._spec])) ]
        

class BuilderCommandOptionsSpecElement(BuilderCommandOptionsSpecAbstract):
    def __init__(self, *, type:str, required:bool=False, default: Any = None, default_ganeti:str='default', **kwargs) -> None:
        super().__init__(**kwargs)
        self.type = type
        self.required = required
        self.default = default
        self.default_ganeti = default_ganeti

    def to_args_spec(self) -> Any:
        return {
            'type': self.type,
            'required': self.required,
            'default': self.default
        }
    
    def to_options(self, ansible_param, info) -> Iterator[str]:
        param_value = self._param_extrator(ansible_param, self.names)
        info_value = self._info_extrator(info, self.info_keys)
        value = self.default_ganeti
        if param_value is not None and info_value != param_value:
            value = param_value
        return [build_single_option(self.name, value)]

class BuilderCommandOptionsSpecSubElement(BuilderCommandOptionsSpecElement):
    def __init__(self, *_, index:int = None, **kwargs) -> None:
        super().__init__(**kwargs)

    def set_index(self, index:int):
        if index is not None:
            self.index = index

    @property
    def info_key(self) -> str:
        if hasattr(self, 'index'):
            return super().info_key.format(self.index)
        return super().info_key

    def to_options(self, ansible_param, info) -> Iterator[str]:
        print(ansible_param)
        print(list(self.names))
        print(list(self.info_keys))
        param_value = self._param_extrator(ansible_param, self.names)
        info_value = self._info_extrator(info, self.info_keys)
        print((param_value, info_value))
        if param_value == info_value:
            return []
        value = self.default_ganeti
        if param_value is not None and info_value != param_value:
            value = param_value
        return ["{}={}".format(self.name, value)]

class BuilderCommandOptionsSpecListSubElement(BuilderCommandOptionsSpecSubElement):
    def __init__(self, *_, default_ganeti='None', **kwargs):
        super().__init__(default_ganeti=default_ganeti, **kwargs)

class BuilderCommandOptions:
    def __init__(self, command:str, spec:BuilderCommandOptionsSpec) -> None:
        self.command:str = command
        self.spec:BuilderCommandOptionsSpec = spec

    def generate(self, module_params: dict, info: dict) -> str:
        pass


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


info = {'Instance name': 'test', 'UUID': '550fc540-dda2-4c11-95a0-6c1de852c11d', 'Serial number': 3, 'Creation time': datetime.datetime(2023, 2, 6, 21, 44, 56), 'Modification time': datetime.datetime(2023, 2, 6, 21, 44, 59), 'State': 'configured to be up, actual state is up', 'Nodes': [{'primary': 'node1', 'group': None}, {'secondaries': None}], 'Operating system': 'noop', 'Operating system parameters': None, 'Allocated network port': None, 'Hypervisor': 'fake', 'Hypervisor parameters': None, 'Back-end parameters': {'always_failover': None, 'auto_balance': None, 'maxmem': None, 'memory': None, 'minmem': None, 'spindle_use': None, 'vcpus': 4}, 'NICs': [{'nic/0': None, 'MAC': 'aa:00:00:6b:2b:d0', 'IP': None, 'mode': 'bridged', 'link': 'br_gnt', 'vlan': None, 'network': None, 'UUID': '1290a6d7-b6ee-4324-ba2c-57c9c3bb61c5', 'name': None}], 'Disk template': 'file', 'Disks': [{'disk/0': 'file, size 10.0G', 'access mode': 'rw', 'logical_id': ['loop', '/srv/ganeti/file-storage/test/8287dcbb-b8fe-4e0e-acdd-6ac909db01f6.file.disk0'], 'on primary': '/srv/ganeti/file-storage/test/8287dcbb-b8fe-4e0e-acdd-6ac909db01f6.file.disk0 (N/A:N/A)', 'name': None, 'UUID': '031b68c5-30b9-4ca4-bfc1-3259384335f1'}]}
param = {"state": "present", "admin_state": "started", "reboot_if_change": False, "params": {"disks": [{"size": "10G"}], "pnode": None, "hypervisor": "kvm", "disk_template": "file", "backend_param": None, "nics": [{"mode": "bridged", "link": "br_gnt", "name": "test"}], "hypervisor_params": None, "name_check": False, "ip_check": False, "iallocator": None, "os_type": "noop"}, "name": "test"}
print(spec.to_args_spec())
print(list(spec.to_options(param,info)))