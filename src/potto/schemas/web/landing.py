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
        return cls(
            title=potto_response.title,
            description=potto_response.description,
            attribution=potto_response.attribution,
            links=[
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
            ]
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
