from typing import (
    Any,
    Protocol,
)

from starlette.datastructures import URL


class UrlResolver(Protocol):

    def __call__(self, route: str, /, **path_param: Any) -> URL:
        ...
