import re
import yaml
from functools import reduce
from typing import List, Any, Callable, Dict

DefaultValidator = Callable[[str], bool]

def dict_get(data:dict, key:str):
    if data is None:
        return None
    return dict.get(data, key)


def recursive_get(data: dict, keys:List[str]) -> Any:
    keys = list(keys)
    if len(keys) == 0:
        return None
    return reduce(dict_get, keys, data)

def info_default_validator(value:str) -> bool:
    if not value:
        return False
    return bool(re.match('default\s+[(][^)]*[)]', value))

def nic_default_validator(value:str) -> bool:
    if value is None:
        return False
    if not value.strip():
        return True
    return bool(re.match('\s*None\s*', value))

def value_info_extractor(data:dict, keys:List[str], default_validator:DefaultValidator=None) -> Any:
    value = recursive_get(data, keys)
    if not isinstance(value, str):
        return value
    if default_validator and default_validator(value):
        return None
    return yaml.safe_load(value)

def size_param_info_extractor(data:dict, keys:List[str]) -> Any:
    value = recursive_get(data, keys)
    if not value or not isinstance(value, str):
        return None
    match = re.search(r'(?P<value>[.0-9]+)(?P<unit>[a-zA-Z])', value)
    if not match:
        return None
    return '{}{}'.format(float(match.group('value')), match.group('unit'))

ValueParamExtractor = Callable[[Dict, List[str]], Any]
ValueInfoExtractor = Callable[[Dict, List[str]], Any]