import json

import pydantic
import shapely

from potto.schemas import pygeoapi_config
from potto.webapp.protocols import UrlResolver


class Feature(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True
    )

    id_: str = pydantic.Field(alias="id")
    properties: dict[str, str | int | float | bool]
    geometry: shapely.Geometry

    @classmethod
    def from_original_feature(cls, original_feature: dict) -> "Feature":
        return cls(
            id=str(original_feature["id"]),
            properties={k: v for k, v in original_feature["properties"].items() if k != "id"},
            geometry=shapely.from_geojson(json.dumps(original_feature["geometry"]))
        )

    def as_jsonld(
            self,
            resource_config: pygeoapi_config.ItemCollectionConfig,
            url_resolver: UrlResolver
    ) -> dict:
        detail_url = url_resolver(
            "get-item",
            collection_id=resource_config.identifier,
            item_id=self.id_
        )
        return {
            "@type": "schema:Place",
            "@id": str(detail_url),
        }
