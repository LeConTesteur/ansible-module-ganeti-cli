import re
import yaml
from functools import reduce
from typing import List, Any, Callable, Dict


def dict_get(data:dict, key:str):
    if data is None:
        return None
    return dict.get(data, key)


def recursive_get(data: dict, keys:List[str]) -> Any:
    if len(keys) == 0:
        return None
    return reduce(dict_get, keys, data)

def value_info_extractor(data:dict, keys:List[str]) -> Any:
    value = recursive_get(data, keys)
    if not isinstance(value, str):
        return value
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