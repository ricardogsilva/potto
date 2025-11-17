import pygeoapi.api
from starlette.exceptions import HTTPException
from starlette.requests import Request


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

