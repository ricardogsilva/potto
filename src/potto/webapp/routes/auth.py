import logging
import secrets

import httpx
import jwt
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from ...auth.oidc import OIDCProvider
from ...config import PottoSettings

logger = logging.getLogger(__name__)

_SESSION_STATE = "oidc_state"
_SESSION_NONCE = "oidc_nonce"
_SESSION_NEXT = "oidc_next"


async def oidc_login(request: Request) -> Response:
    """Redirect the browser to the OIDC provider's authorization endpoint."""
    oidc_provider: OIDCProvider = request.state.oidc_provider

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    request.session[_SESSION_STATE] = state
    request.session[_SESSION_NONCE] = nonce
    request.session[_SESSION_NEXT] = request.query_params.get("next", "/")

    await oidc_provider.get_discovery()
    redirect_uri = str(request.url_for("oidc-callback"))
    auth_url = oidc_provider.get_authorization_url(redirect_uri, state, nonce)
    return RedirectResponse(auth_url)


async def oidc_callback(request: Request) -> Response:
    """Handle the authorization code callback from the OIDC provider."""
    oidc_provider: OIDCProvider = request.state.oidc_provider
    settings: PottoSettings = request.state.settings

    expected_state = request.session.pop(_SESSION_STATE, None)
    request.session.pop(_SESSION_NONCE, None)
    next_url = request.session.pop(_SESSION_NEXT, "/")

    error = request.query_params.get("error")
    if error:
        description = request.query_params.get("error_description", "")
        logger.warning(f"OIDC provider returned error: {error}: {description}")
        return Response(f"Authentication error: {error}", status_code=400)

    if request.query_params.get("state") != expected_state:
        return Response("Invalid state parameter", status_code=400)

    code = request.query_params.get("code")
    if not code:
        return Response("Missing authorization code", status_code=400)

    redirect_uri = str(request.url_for("oidc-callback"))
    try:
        token_response = await oidc_provider.exchange_code(code, redirect_uri)
    except httpx.HTTPStatusError as exc:
        logger.error(f"OIDC token exchange failed: {exc}")
        return Response("Token exchange failed", status_code=502)

    id_token = token_response.get("id_token")
    if not id_token:
        logger.error("OIDC token response contained no id_token")
        return Response("No id_token in token response", status_code=502)

    try:
        claims = await oidc_provider.validate_id_token(id_token)
    except jwt.InvalidTokenError as exc:
        logger.error(f"ID token validation failed: {exc}")
        return Response("Invalid ID token", status_code=400)

    access_token = token_response.get("access_token")
    if access_token:
        try:
            access_claims = await oidc_provider.validate_access_token(access_token)
            claims = {**claims, **access_claims}
        except jwt.InvalidTokenError as exc:
            logger.warning(f"Access token validation failed, using ID token claims only: {exc}")

    async with settings.get_db_session_maker()() as session:
        db_user = await oidc_provider.provision_user(session, claims)

    if not db_user.is_active:
        return Response("Account is disabled", status_code=403)

    # Sync scopes from token claims to DB if roles_claim is configured
    scopes = oidc_provider.extract_scopes(claims)
    if scopes and scopes != db_user.scopes:
        async with settings.get_db_session_maker()() as session:
            db_user.scopes = scopes
            session.add(db_user)
            await session.commit()

    request.session["user_id"] = str(db_user.id)
    request.session["id_token"] = id_token
    return RedirectResponse(next_url, status_code=303)
