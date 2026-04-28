"""
Pygeoapi providers that store their data directly in the pygeoapi
configuration file.

These are useful mainly for testing
"""

from typing import (
    Any,
    Protocol,
)


class PygeoapiFeatureProviderProtocol(Protocol):
    name: str
    type: str
    data: Any
    storage_crs: str

    def __init__(self, provider_definition: dict) -> None: ...

    def get_schema(self) -> dict:
        """Return a JSON schema representation of the data"""

#     def query(
#             self,
#             offset: int = 0,
#             limit: int = 10,
#             resulttype: str = "results",
#             bbox: list[Any] | None = None,
#             datetime_=None,
#             properties: list[Any] | None = None,
#             sortby=[],
#             select_properties=[],
#             skip_geometry=False,
#             q=None,
#             filterq=None,
#             crs_transform_spec=None,
#             **kwargs
#     ) -> dict:
#         ...
#
#     def get(self, identifier: Any, **kwargs) -> dict:
#
# class PygeoapiConfigGeoJsonProvider: