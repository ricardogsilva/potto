import babel
import pygeoapi.api
import pygeoapi.l10n
from starlette.exceptions import HTTPException
from starlette.requests import Request


def set_html_link_self_relation(original_links: list[dict]) -> list[dict]:
    """Modify input list of links so that the HTML link has `rel=self`.

    As HTML is always rendered outside pygeoapi core, this means links generated
    by pygeoapi will never have an HTML-related link with a relation of 'self'.

    This function can be used to ensure the list of links has the `self`
    relation set on the link that points to an HTML resource.
    """
    result = []
    for link in original_links:
        new_link = link.copy()
        if link["rel"] == "self":
            new_link["rel"] = "alternate"
            result.append(new_link)
        elif link["type"] == pygeoapi.api.FORMAT_TYPES[pygeoapi.api.F_HTML]:
            new_link["rel"] = "self"
            result.append(new_link)
        else:
            result.append(new_link)
    return result


def get_localized_pygeoapi_config(
        pygeoapi_config: dict, current_language: str) -> dict:
    return pygeoapi.l10n.translate_struct(
        pygeoapi_config,
        locale_=babel.Locale.parse(current_language),
        is_config=True
    )


def get_requested_media_type(request: Request) -> str:
    return (
            pygeoapi.api.FORMAT_TYPES.get(request.query_params.get("f"))
            or request.headers.get("Accept", "application/json")
    )


def check_media_type(
        requested: str,
        able_to_serve_nicknames: list[str] | None = None
):
    able_to_serve = able_to_serve_nicknames or [
        pygeoapi.api.F_JSON,
        pygeoapi.api.F_HTML
    ]
    if not any(
            (
                    requested in ("*", "*/*"),
                    *(nickname in requested for nickname in able_to_serve),
            )
    ):
        raise HTTPException(
            406, "Cannot produce response in the requested media type"
        )

