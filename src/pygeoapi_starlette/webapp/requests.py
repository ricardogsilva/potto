import logging
from typing import Mapping

import babel
import pygeoapi.api
import pygeoapi.l10n
import pygeoapi.util
from starlette.requests import Request

from ..config import PygeoapiStarletteSettings

logger = logging.getLogger(__name__)


class PygeoapiRequest:
    """Mimics pygeoapi's APIRequest class

    Pygeoapi's APIRequest class is a wrapper around each supported framework's
    own request class.

    In the context of pygeoapi-starlette we don't care about the complexities
    involved in parsing other frameworks' requests, so this is a slimmed-down
    version of `pygeoapi.api.APIRequest` with just starlette-related things.

    Note that this does not inherit from APIRequest on purpose. Hopefully,
    one day pygeoapi will sunset its own APIRequest class and make pygeoapi
    core request handlers accept just the relevant parameters as inputs. Not
    inheriting from pygeoapi's APIRequest makes us more independent from it.
    """

    _prefer_format: str | None
    _request: Request

    def __init__(
            self,
            original_request: Request,
            output_format: str | None = None,
    ) -> None:
        self._prefer_format = output_format
        self._request = original_request

    @property
    def data(self) -> bytes:
        ...

    @property
    def params(self) -> Mapping[str, str]:
        return self._request.query_params

    @property
    def path_info(self) -> str:
        return self._request.scope["path"].strip("/")

    @property
    def locale(self) -> babel.Locale:
        logger.debug(f"{self.raw_locale=}")
        return babel.Locale.parse(self.raw_locale, sep="-")

    @property
    def raw_locale(self) -> str:
        settings: PygeoapiStarletteSettings = self._request.state.settings

        # get locale from the 'lang' query param first
        if requested_param := self._request.query_params.get(
                pygeoapi.l10n.QUERY_PARAM):
            return requested_param

        # as an alternative, get it from the Accept-Language request header,
        # falling back to the default specified in the settings
        chosen_lang = pygeoapi.util.get_choice_from_headers(
            self._request.headers,
            "Accept-Language",
            all=False
        ) or "*"
        chosen_lang: str
        return chosen_lang if chosen_lang != "*" else settings.locales[0]

    @property
    def format(self) -> str:
        # This property is crucial for determining the output gotten from
        # pygeoapi.

        # This behaves quite differently from vanilla pygeoapi's `APIRequest.format`:
        # - It may choose to return a predefined format - this is mainly use to force
        #   pygeoapi to render a specific response type, e.g. `jsonld`
        # - Always returns a value
        # - never returns `HTML` as a result. The reason being that
        #   core pygeoapi tries to render results to HTML when the request has
        #   this format. We want to offload rendering of HTML from pygeoapi core,
        #   so we never use it here

        if self._prefer_format:
            return self._prefer_format

        default_format = pygeoapi.api.F_JSON

        if f_param := self._request.query_params.get("f"):
            return f_param if f_param != pygeoapi.api.F_HTML else default_format

        result = default_format
        if (
                accepted_media_types := pygeoapi.util.get_choice_from_headers(
                    self._request.headers,
                    "accept",
                    all=True
                )
        ) is None:
            return result

        for nickname, media_type in pygeoapi.api.FORMAT_TYPES.items():
            if nickname == pygeoapi.api.F_HTML:
                continue
            for accepted in accepted_media_types:
                if accepted == media_type:
                    result = nickname
                    break
        return result

    @property
    def headers(self) -> Mapping[str, str]:
        return self._request.headers

    def get_linkrel(self, format_: str) -> str:
        return "self" if format_.lower() == self.format else "alternate"

    def is_valid(
            self,
            additional_formats: list[str] | None = None
    ) -> bool:
        if self.format in pygeoapi.api.FORMAT_TYPES.keys():
            return True
        if self.format in (f.lower() for f in (additional_formats or ())):
            return True
        return False

    def get_response_headers(
            self,
            force_lang: babel.Locale | None = None,
            force_type: str | None = None,
            force_encoding: str | None = None,
            **custom_headers: str
    ) -> dict[str, str]:
        # note: don't set 'Content-Encoding', GZipMiddleware is already
        # enabled in the starlette app
        return {
            "Content-Type": (
                    force_type or pygeoapi.api.FORMAT_TYPES[self.format]
            ),
            "X-Powered-By": f"pygeoapi {pygeoapi.__version__}",
            "Content-Language": force_lang.language if force_lang else self.raw_locale,
            **custom_headers,
        }
