import asyncio
import json
import logging
from typing import (
    Protocol,
    Literal,
    Sequence,
    TypeAlias,
)

import babel
import shapely
from starlette.authentication import BaseUser
from pygeoapi.api import (
    API as _API,
    evaluate_limit as _evaluate_limit,
    F_JSON,
    FORMAT_TYPES as _FORMAT_TYPES,
)
from pygeoapi.api.itemtypes import (
    get_collection_items as _get_collection_items,
    get_collection_item as _get_collection_item,
)
from pygeoapi.openapi import get_oas_30
from pygeoapi.l10n import translate_struct

from . import constants
from .config import PottoSettings
from .db.queries.metadata import get_metadata
from .db.queries.collections import paginated_list_collections
from .exceptions import PottoException
from .operations.config import get_pygeoapi_config
from .operations import collections as collection_operations
from .schemas import (
    base,
    potto as potto_schemas,
)
from .schemas.items import Feature
from .schemas.web.items import FeatureFilter
from .schemas.pygeoapi_config import ItemCollectionConfig
from .webapp.requests import PottoRequest

logger = logging.getLogger(__name__)

ResourceTypes: TypeAlias = Sequence[Literal["collection", "stac-collection", "process"]]


class Potto:
    """A wrapper around pygeoapi core.

    This wrapper presents a simpler interface than pygeoapi core and also
    implements some additional operations.

    The major difference from pygeoapi core is that this wrapper's methods
    accept direct arguments rather than receiving a generic `Request` class
    and then parsing the contents of the request. This means that this class
    demands that parsing of an HTTP request be done before calling it, or in
    other words, that the framework that is wrapping pygeoapi core deals with
    the complexity of retrieving parameters from the HTTP request.

    Note that internally this class' methods still need to construct a
    `Request` instance in order to send to pygeoapi core, which expects it.
    But the interface they present to the world is request-free. This is done
    with two intentions:

    - Allow non HTTP clients to use pygeoapi core. For example, a CLI
      application
    - Demonstrate what pygeoapi core's public API would look like if it did
      not focus on parsing HTTP Requests but rather whatever input parameters
      were needed for each particular method
    """
    _settings: PottoSettings

    def __init__(
            self,
            settings: PottoSettings,
    ) -> None:
        self._settings = settings

    async def _get_pygeoapi(
            self,
            user: BaseUser,
            collection_page: int = 1,
            collection_page_size: int = 20,
    ) -> _API:
        async with self._settings.get_db_session_maker()() as session:
            pygeoapi_config = await get_pygeoapi_config(
                session, self._settings, user,
                collection_page=collection_page,
                collection_page_size=collection_page_size
            )
        openapi_document = get_oas_30(pygeoapi_config, fail_on_invalid_collection=True)
        return _API(config=pygeoapi_config, openapi=openapi_document)

    async def _get_collection(
            self,
            collection_id: str,
            user: BaseUser,
    ) -> potto_schemas.Collection | None:
        collection_retriever = self._settings.get_collection_retriever()
        return await collection_retriever.get_collection(
            self._settings,
            collection_identifier=collection_id,
            user=user
        )

    async def get_localized_config(self, locale: babel.Locale) -> dict:
        pygeoapi_api = await self._get_pygeoapi()
        return translate_struct(
            pygeoapi_api.config,
            locale_=locale,
            is_config=True
        )

    async def api_get_landing_page(
            self,
            *,
            user: BaseUser,
            language: str | None = None,
    ) -> potto_schemas.LandingPage:
        """Return overview information.

        The response contains useful info for generating a landing page for the API.
        """
        collection_retriever = self._settings.get_collection_retriever()
        collection_list = await collection_retriever.list_collections(self._settings, user=user)
        server_metadata_retriever = self._settings.get_server_metadata_retriever()
        server_metadata = await server_metadata_retriever.get_server_metadata(self._settings, user=user)
        return potto_schemas.LandingPage(
            metadata=server_metadata,
            attribution=None,
            collections=collection_list,
        )

    async def api_get_conformance_details(self) -> potto_schemas.ConformanceDetail:
        return potto_schemas.ConformanceDetail(
            conforms_to=[
                constants.CONFORMANCE_CLASS_OGCAPI_FEATURES_CORE,
                constants.CONFORMANCE_CLASS_OGCAPI_FEATURES_GEOJSON,
                constants.CONFORMANCE_CLASS_OGCAPI_FEATURES_OPENAPI3
            ]
        )

    async def api_get_openapi_document(
            self,
    ) -> potto_schemas.PottoResponse:
        pygeoapi_api = await self._get_pygeoapi()
        return potto_schemas.PottoResponse(
            content_type=_FORMAT_TYPES[F_JSON],
            content=pygeoapi_api.openapi
        )

    async def api_list_collection_items(
            self,
            collection_id: str,
            *,
            locale: babel.Locale,
            filter_: FeatureFilter | None = None,
    ) -> potto_schemas.FeatureListResponse:
        async with self._settings.get_db_session_maker()() as session:
            if not (
                db_collection := await collection_operations.get_collection_by_resource_identifier(
                    session, collection_id)
            ):
                raise PottoException(f"Collection {collection_id} not found")
        pygeoapi_api = await self._get_pygeoapi(
            resource_types=["collection"],
            resource_page_size=None
        )
        pygeoapi_response = await asyncio.to_thread(
            _get_collection_items,
            pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format="json",
                **(filter_.model_dump(by_alias=True, exclude_none=True) if filter_ else {})
            ),
            dataset=collection_id
        )
        pygeoapi_headers, pygeoapi_status_code, pygeoapi_content = pygeoapi_response
        parsed_pygeoapi_content = json.loads(pygeoapi_content)
        logger.debug(f"{parsed_pygeoapi_content=}")
        collection_config = await self.get_item_collection_config(collection_id)
        features=[
            Feature.from_original_feature(feat)
            for feat in parsed_pygeoapi_content["features"]
        ]
        return potto_schemas.FeatureListResponse(
            collection=db_collection,
            features=features,
            pagination=base.PaginationContext(
                limit=_evaluate_limit(
                    requested=filter_.limit if filter_ else None,
                    server_limits=pygeoapi_api.config["server"].get("limits", {}),
                    collection_limits=(
                        col_limits.as_pygeoapi_config
                        if (col_limits := collection_config.limits) else {}
                    ),
                ),
                number_matched=parsed_pygeoapi_content.get("numberMatched", 0),
                number_returned=parsed_pygeoapi_content.get("numberReturned", len(features)),
                offset=parsed_pygeoapi_content.get("offset", 0),
            ),
            filter_=filter_,
            metadata={
                **pygeoapi_headers,
                "timestamp": parsed_pygeoapi_content.get("timeStamp"),
            },
        )

    async def api_get_item(
            self,
            *,
            item_id: str,
            collection_id: str,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> potto_schemas.FeatureResponse:
        async with self._settings.get_db_session_maker()() as session:
            if not (
                    db_collection := await collection_operations.get_collection_by_resource_identifier(
                        session, collection_id)
            ):
                raise PottoException(f"Collection {collection_id} not found")
        pygeoapi_api = await self._get_pygeoapi(
            resource_types=["collection"], resource_page_size=None)
        pygeoapi_response = await asyncio.to_thread(
            _get_collection_item,
            pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=collection_id,
            identifier=item_id,
        )
        pygeoapi_headers, pygeoapi_status_code, pygeoapi_content = pygeoapi_response
        parsed_pygeoapi_content = json.loads(pygeoapi_content)
        return potto_schemas.FeatureResponse(
            collection=db_collection,
            feature=Feature.from_original_feature(parsed_pygeoapi_content),
            metadata=pygeoapi_headers
        )
