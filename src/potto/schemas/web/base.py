from typing import Annotated

import pydantic

from ... import constants
from ...webapp.protocols import UrlResolver
from ..base import Link
from ..potto import LandingPage


class JsonLanding(pydantic.BaseModel):
    links: list[Link]
    title: str | None = None
    description: str | None = None
    attribution: str | None = None

    @classmethod
    def from_potto(
            cls,
            potto_response: LandingPage,
            url_resolver: UrlResolver
    ) -> "JsonLanding":
        links = [
            Link(
                type=constants.MEDIA_TYPE_JSON,
                rel=constants.REL_SELF,
                href=str(url_resolver("api:landing-page")),
                title="This resource"
            ),
            Link(
                type=constants.MEDIA_TYPE_HTML,
                rel=constants.REL_ALTERNATE,
                href=str(url_resolver("landing-page")),
                title="HTML landing page"
            ),
            Link(
                type=constants.MEDIA_TYPE_JSON,
                rel=constants.REL_SERVICE_DESC,
                href=str(url_resolver("api:openapi")),
                title="OpenAPI document"
            ),
            Link(
                type=constants.MEDIA_TYPE_JSON,
                rel=constants.REL_SERVICE_DOC,
                href=str(url_resolver("api:swagger_ui_html")),
                title="API documentation"
            ),
            Link(
                type=constants.MEDIA_TYPE_JSON,
                rel=constants.REL_CONFORMANCE,
                href=str(url_resolver("api:conformance-page")),
                title="API conformance declaration"
            ),
        ]
        if any(
                c for c in potto_response.collections
                if c.item_type == constants.FEATURE_COLLECTION_ITEM_TYPE
        ):
            links.extend([
                Link(
                    type=constants.MEDIA_TYPE_JSON,
                    rel=constants.REL_COLLECTIONS,
                    href=str(url_resolver("api:list-collections")),
                    title="Collections exposed by this server"
                ),
            ])
        return cls(
            title=potto_response.title,
            description=potto_response.description,
            attribution=potto_response.attribution,
            links=links
        )


class HtmlLanding(JsonLanding):

    @classmethod
    def from_potto(
            cls,
            potto_response: LandingPage,
            url_resolver: UrlResolver
    ) -> "HtmlLanding":
        return cls(
            title=potto_response.title,
            description=potto_response.description,
            attribution=potto_response.attribution,
            links=[
                Link(
                    type=constants.MEDIA_TYPE_HTML,
                    rel=constants.REL_SELF,
                    href=str(url_resolver("landing-page")),
                    title="This resource"
                ),
                Link(
                    type=constants.MEDIA_TYPE_JSON,
                    rel=constants.REL_ALTERNATE,
                    href=str(url_resolver("api:landing-page")),
                    title="JSON landing page"
                ),
            ]
        )


class JsonConformance(pydantic.BaseModel):
    conforms_to: Annotated[list[str], pydantic.Field(alias="conformsTo")]