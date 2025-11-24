from typing import Literal

import pydantic


class LimitsConfig(pydantic.BaseModel):
    max_items: int = 100
    default_items: int = 10
    max_distance_x: float = 100
    max_distance_y: float = 100
    max_distance_units: str = ""
    on_exceed: Literal["error", "throttle"] = "throttle"

    @classmethod
    def from_raw_config(cls, raw_config: dict) -> "LimitsConfig":
        return cls(
            max_items=raw_config.get("max_items", 100),
            default_items=raw_config.get("default_items", 10),
            max_distance_x=raw_config.get("max_distance", {}).get("x", 100),
            max_distance_y=raw_config.get("max_distance", {}).get("y", 100),
            max_distance_units=raw_config.get("max_distance_units", ""),
            on_exceed=raw_config.get("on_exceed", "throttle"),
        )


class LinkConfig(pydantic.BaseModel):
    type_: str
    rel: str
    href: str
    title: str | None = None
    href_lang: str | None = None
    length: int | None = None

    @classmethod
    def from_raw_config(cls, raw_config: dict) -> "LinkConfig":
        return cls(
            type_=raw_config["type"],
            rel=raw_config["rel"],
            href=raw_config["href"],
            title=raw_config.get("title"),
            href_lang=raw_config.get("hreflang"),
            length=int(length) if (length :=raw_config.get("length")) else None,
        )



class SpatialExtentConfig(pydantic.BaseModel):
    bbox: list[float]
    crs: str = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"


class TemporalExtentConfig(pydantic.BaseModel):
    begin: str | None
    end: str | None
    trs: str = "http://www.opengis.net/def/uom/ISO-8601/0/Gregorian"


class ExtentConfig(pydantic.BaseModel):
    spatial: SpatialExtentConfig
    temporal: TemporalExtentConfig | None = None

    @classmethod
    def from_raw_config(cls, raw_config: dict) -> "ExtentConfig":
        return cls(
            spatial=SpatialExtentConfig(
                bbox=raw_config["spatial"]["bbox"],
                crs=raw_config["spatial"].get(
                    "crs", "http://www.opengis.net/def/crs/OGC/1.3/CRS84")
            ),
            temporal=TemporalExtentConfig(
                begin=raw_temporal_config.get("begin"),
                end=raw_temporal_config.get("end"),
                trs=raw_temporal_config.get(
                    "trs", "http://www.opengis.net/def/uom/ISO-8601/0/Gregorian")
            ) if (raw_temporal_config := raw_config.get("temporal")) else None
        )


class FormatConfig(pydantic.BaseModel):
    name: str
    media_type: str

    @classmethod
    def from_raw_config(cls, raw_config: dict) -> "FormatConfig":
        return cls(
            name=raw_config["name"],
            media_type=raw_config["mimetype"]
        )


class ProviderConfig(pydantic.BaseModel):
    type_: Literal[
        "coverage",
        "edr",
        "feature",
        "map",
        "record",
        "stac",
        "tile",
    ]
    name: str
    data_: str | dict
    is_default_for_collection: bool = False
    is_editable: bool = False
    table: str | None = None
    id_field: str | None = None
    geometry_x_field: str | None = None
    geometry_y_field: str | None = None
    time_field: str | None = None
    title_field: str | None = None
    default_format: FormatConfig = None
    extra_options: dict | None = None
    properties_to_return: list[str] | None = pydantic.Field(min_length=1)
    supported_crs: list[str] | None = None
    storage_crs: str = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
    storage_crs_coordinate_epoch: str | None = None
    include_extra_query_parameters: bool = True

    @classmethod
    def from_raw_config(cls, raw_config: dict) -> "ProviderConfig":
        return cls(
            type_=raw_config["type"],
            name=raw_config["name"],
            data_=raw_config["data_"],
            is_default_for_collection=raw_config.get("default", False),
            is_editable=raw_config.get("editable", False),
            table=raw_config.get("table"),
            id_field=raw_config.get("id_field"),
            geometry_x_field=raw_config.get("geometry", {}).get("x_field"),
            geometry_y_field=raw_config.get("geometry", {}).get("y_field"),
            time_field=raw_config.get("time_field"),
            title_field=raw_config.get("title_field"),
            default_format=FormatConfig.from_raw_config(raw_format) if (raw_format := raw_config.get("format")) else None,
            extra_options=raw_config.get("options"),
            properties_to_return=raw_config.get("properties"),
            supported_crs=raw_config.get("crs"),
            storage_crs=raw_config.get("storage_crs", "http://www.opengis.net/def/crs/OGC/1.3/CRS84"),
            storage_crs_coordinate_epoch=raw_config.get("storage_crs_coordinate_epoch"),
            include_extra_query_parameters=raw_config.get("include_extra_query_parameters"),
        )


class ItemCollectionConfig(pydantic.BaseModel):
    type_: Literal["collection"]
    title: str
    description: str
    keywords: list[str]
    extents: ExtentConfig
    providers: list[ProviderConfig]
    visibility: Literal["default", "hidden"] = "default"
    linked_data: dict | None = None
    links: list[LinkConfig] | None = None
    limits: LimitsConfig | None = None

    def list_provider_configs(
            self,
            type_: Literal[
                "feature",
                "coverage",
                "record",
                "map",
                "tile",
                "edr",
                "stac",
            ] | None = None
    ):
        return [p for p in self.providers if p.type_ == type_] if type_ else self.providers

    def get_default_provider_config(
            self,
            type_: Literal[
                "feature",
                "coverage",
                "record",
                "map",
                "tile",
                "edr",
                "stac",
            ] | None = None
    ) -> ProviderConfig:
        for provider_conf in self.providers:
            if provider_conf.is_default_for_collection:
                return provider_conf
        if type_:
            return [p for p in self.providers if p.type_ == type_][0]
        else:
            return self.providers[0]

    @classmethod
    def from_raw_config(cls, raw_config: dict) -> "ItemCollectionConfig":
        return cls(
            type_=raw_config["type"],
            title=raw_config["title"],
            description=raw_config["description"],
            keywords=raw_config["keywords"],
            extents=ExtentConfig.from_raw_config(raw_config["extents"]),
            providers=[
                ProviderConfig.from_raw_config(raw_provider)
                for raw_provider in raw_config["providers"]
            ],
            visibility=raw_config.get("visibility", "default"),
            linked_data=raw_config.get("linked_data"),
            links=[
                LinkConfig.from_raw_config(raw_link) for raw_link in raw_links
            ] if (raw_links:=raw_config.get("links")) else None,
            limits=LimitsConfig.from_raw_config(raw_limits) if (raw_limits:=raw_config.get("limits")) else None,
        )
