from pygeoapi.util import (
    DATETIME_FORMAT,
    to_json as _to_json,
    format_datetime as _format_datetime,
    format_duration as _format_duration,
    human_size as _human_size,
    get_path_basename as _get_path_basename,
    get_breadcrumbs as _get_breadcrumbs,
    filter_dict_by_key_value as _filter_dict_by_key_value,
)


def to_json(data_: dict, pretty: bool = False) -> str:
    return _to_json(data_, pretty)


def format_datetime(value: str, format_: str = DATETIME_FORMAT) -> str:
    return _format_datetime(value, format_)


def format_duration(start: str, end: str = None) -> str:
    return _format_duration(start, end)


def human_size(nbytes: int) -> str:
    return _human_size(nbytes)


def get_path_basename(urlpath: str) -> str:
    return _get_path_basename(urlpath)


def get_breadcrumbs(urlpath: str) -> list:
    return _get_breadcrumbs(urlpath)


def filter_dict_by_key_value(data_: dict, key: str, value: str) -> dict:
    return _filter_dict_by_key_value(data_, key, value)