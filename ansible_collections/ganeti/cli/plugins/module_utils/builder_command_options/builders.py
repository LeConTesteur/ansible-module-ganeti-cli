"""Command add and modify options builder
"""
import abc
import copy
from functools import wraps
from itertools import chain, zip_longest
from typing import Any, Dict, Iterator, List, Callable
from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options.builder_functions \
    import (
        build_options_with_prefixes,
        build_prefixes_from_count_diff,
        build_single_option,
        build_state_option,
        build_sub_dict_options
    )
from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options.extractors import (
    ValueInfoExtractor,
    ValueParamExtractor,
    recursive_get,
    value_info_extractor
)


from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options.prefixes import (
    Prefix,
    PrefixIndex,
    PrefixNone,
)


DEFAULT_VALUE= 'default'
NONE_VALUE= 'None'
IGNORE_INFO_KEY = object()

PrefixBuilder = Callable[[Any, Any], Prefix]

def recurcive(property_name:str):
    """Create recurcive method

    Args:
        property_name (str): Name of property in method
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self) -> Iterator[str]:
            it = [getattr(self, property_name)] # pylint: disable=invalid-name
            if self.parent is None:
                return it
            return filter(lambda x:x, chain(getattr(self.parent, func.__name__)(), it))
        return wrapper
    return decorator

# pylint: disable=too-many-instance-attributes
class BuilderCommandOptionsSpecAbstract:
    """Abstract builder
    """
    def __init__(
            self, *,
            parent = None,
            name:str,
            info_key:str=None,
            param_extractor:ValueParamExtractor=recursive_get,
            info_extractor:ValueInfoExtractor=value_info_extractor,
            create_only=False,
            **kwargs
        ) -> None:
        self._name = name
        self._info_key = info_key
        self.parent = parent
        self._param_extractor = param_extractor
        self._info_extractor = info_extractor
        self._extra_args = kwargs
        self._create_only = create_only
        self._default = kwargs.get('default')

    def __repr__(self) -> str:
        return 'Spec: {} -> {}'.format(self._name, self._info_key)

    @property
    def name(self) -> str:
        """Name of argument in config

        Returns:
            str: The name
        """
        return self._name

    @recurcive('name')
    def names(self) -> Iterator[str]:
        """List of name for create fullname

        Yields:
            Iterator[str]: The names
        """

    @property
    def info_key(self) -> str:
        """Get the key in information returned by ganeti command

        Returns:
            str: The key
        """
        if self._info_key == IGNORE_INFO_KEY:
            return None
        return self._info_key or self.name

    @recurcive('info_key')
    def info_keys(self) -> Iterator[str]:
        """List of info key for create fullname

        Yields:
            Iterator[str]: The information keys
        """

    @abc.abstractmethod
    def to_args_spec(self) -> Dict:
        """Generate ansible module args spec

        Returns:
            Dict: the arguments specification
        """

    def to_options(self, ansible_param:dict, info:dict, create:bool) -> Iterator[str]:
        """Generate command options

        Args:
            ansible_param (dict): The ansible module param
            info (dict): The vm information
            create (bool): Option when create

        Returns:
           Iterator[str]: The list of command options

        Yields:
            Iterator[str]: The list of command options
        """
        if self._create_only and not create:
            return []
        return self._to_options(
            ansible_param=ansible_param,
            info=info,
            create=create
        )

    @abc.abstractmethod
    def _to_options(self, ansible_param:dict, info:dict, create:bool) -> Iterator[str]:
        """Generate command options

        Args:
            ansible_param (dict): The ansible module param
            info (dict): The vm information
            create (bool): Option when create

        Returns:
           Iterator[str]: The list of command options

        Yields:
            Iterator[str]: The list of command options
        """


class BuilderCommandOptionsSpec(BuilderCommandOptionsSpecAbstract):
    """Builder of generic spec
    """
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract], **kwargs) -> None:
        super().__init__(**kwargs)
        self._spec = args
        for _spec in self._spec:
            _spec.parent = self


    def to_args_spec(self) -> Dict:
        return {
            spec.name: spec.to_args_spec() for spec in self._spec
        }

    def _to_options(self, ansible_param, info, create) -> Iterator[str]:
        return chain(*[spec.to_options(ansible_param, info, create) for spec in self._spec])

class BuilderCommandOptionsRootSpec(BuilderCommandOptionsSpec):
    """The root Builder spec
    """
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract]) -> None:
        super().__init__(*args, name='params', info_key=IGNORE_INFO_KEY)

    def to_args_spec(self) -> Dict:
        return {
            'type': 'dict',
            'required': False,
            'options': super().to_args_spec(),
        }

class BuilderCommandOptionsSpecDict(BuilderCommandOptionsSpec):
    """Dictionnary Builder Spec
    """
    def __init__(
            self,
            *args: List[BuilderCommandOptionsSpecAbstract],
            prefix_builder: PrefixBuilder = None,
            **kwargs
        ) -> None:
        super().__init__(*args, **kwargs)
        self.prefix_builder = prefix_builder

    def to_args_spec(self) -> Dict:
        return {
            'type': 'dict',
            'required': False,
            'options': super().to_args_spec(),
        }

    def _to_options(self, ansible_param, info, create) -> List[str]:
        prefix = PrefixNone()
        if self.prefix_builder is not None:
            prefix = self.prefix_builder(ansible_param, info)
        option = ','.join(
            chain.from_iterable(
                [spec.to_options(ansible_param, info, create) for spec in self._spec]
                )
            )
        return [ build_options_with_prefixes(
                [option] if option else [],
                option_name=self.name,
                prefixes=prefix
        )]

class BuilderCommandOptionsSpecList(BuilderCommandOptionsSpec):
    """List Builder
    """
    def __init__(
            self, *args: List[BuilderCommandOptionsSpecAbstract], no_option:str = None, **kwargs
        ) -> None:
        super().__init__(*args, **kwargs)
        self.no_option = no_option

    def to_args_spec(self) -> Dict:
        return {
            'type': 'list',
            'required': False,
            'options': super().to_args_spec(),
        }

    def _to_options(self, ansible_param, info, create) -> Iterator[str]:
        param_value = self._param_extractor(ansible_param, self.names()) or []
        info_value = self._info_extractor(info, self.info_keys()) or []
        size_param_list, size_info_list = len(param_value), len(info_value)
        value = []
        if size_param_list == 0 and self.no_option:
            value.append(self.no_option)
        if not create:
            prefixes = list(build_prefixes_from_count_diff(size_param_list, size_info_list))
        else:
            prefixes = PrefixIndex()

        value.append(
            build_options_with_prefixes(
                chain.from_iterable([
                    _BuilderCommandOptionsSpecListElement(*self._spec, index=index)
                        .to_options(value[0], value[1], create)
                    for index, value in enumerate(
                            zip_longest(param_value, info_value, fillvalue={})
                        )
                ]),
                self.name,
                prefixes=prefixes
                )
        )
        return value


class _BuilderCommandOptionsSpecListElement(BuilderCommandOptionsSpecAbstract):
    """Intermediate Element list builder for remove parent names and information
    """
    def __init__(self, *args: List[BuilderCommandOptionsSpecAbstract], index:int = None) -> None:
        super().__init__(parent=None, name=None, info_key=None)
        self._spec = copy.deepcopy(args)
        for spec in self._spec:
            spec.parent = self
            spec.set_index(index)

    def to_args_spec(self) -> Dict:
        pass

    def _to_options(self, ansible_param, info, create) -> Iterator[str]:
        return [
            ','.join(
                chain.from_iterable(
                    [spec.to_options(ansible_param, info, create) for spec in self._spec])
                )

            ]


class BuilderCommandOptionsSpecElement(BuilderCommandOptionsSpecAbstract):
    """Element builder for top specification
    """
    def __init__(
        self, *, default_ganeti:str=DEFAULT_VALUE, build_function=build_single_option, **kwargs
        ) -> None:
        super().__init__(**kwargs)
        self.default_ganeti = default_ganeti
        self.build_function = build_function

    def to_args_spec(self) -> Dict:
        return self._extra_args

    def _to_options(self, ansible_param, info, create) -> Iterator[str]:
        param_value = self._param_extractor(ansible_param, self.names())
        info_value = self._info_extractor(info, self.info_keys())
        if param_value == info_value:
            return []
        value = self._default or self.default_ganeti
        if param_value is not None and info_value != param_value:
            value = param_value
        return [self.build_function(self.name, value)]

class BuilderCommandOptionsSpecSubElement(BuilderCommandOptionsSpecElement):
    """Sub generic element builder
    """
    def __init__(self, *_, index:int = None, **kwargs) -> None:
        super().__init__(build_function=build_sub_dict_options,**kwargs)
        self.set_index(index)

    def __repr__(self) -> str:
        index = ''
        if hasattr(self, 'index'):
            index =  ' / {}'.format(self.index)
        return '{}{}'.format(super().__repr__(), index)

    def set_index(self, index:int):
        """Set index of this element in list"""
        if index is not None:
            self.index = index

    @property
    def info_key(self) -> str:
        if hasattr(self, 'index'):
            return super().info_key.format(self.index)
        return super().info_key

class BuilderCommandOptionsSpecListSubElement(BuilderCommandOptionsSpecSubElement):
    """List element builder
    """
    def __init__(self, *_, default_ganeti=NONE_VALUE, **kwargs):
        super().__init__(default_ganeti=default_ganeti, **kwargs)

class BuilderCommandOptionsSpecElementOnlyCreate(BuilderCommandOptionsSpecElement):
    """Spec builder for option only create step
    """
    def __init__(self, *, create_only=True, build_function=build_single_option, **kwargs) -> None:
        super().__init__(build_function=build_function, create_only=create_only, **kwargs)

class BuilderCommandOptionsSpecStateElement(BuilderCommandOptionsSpecElementOnlyCreate):
    """State builder
    """
    def __init__(self, *_, default=True, **kwargs) -> None:
        super().__init__(type='bool', default=default, build_function=build_state_option, **kwargs)


class BuilderCommand:
    """Generate final command options"""
    def __init__(self, spec:BuilderCommandOptionsSpec) -> None:
        self.spec = spec

    def generate_args_spec(self) -> Dict:
        """Generate Args spec"""
        return self.spec.to_args_spec()

    def generate(
            self,
            *extra_options:List[str],
            module_params: dict,
            info_data: dict,
            create:bool=False
        ) -> str:
        """Generate Options"""
        return ' '.join(
            filter(
                lambda x:x,
                chain(
                    extra_options,
                    self.spec.to_options(module_params, info_data, create)
                )
            )
        )
