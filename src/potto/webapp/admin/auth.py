import uuid

import bcrypt
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed

from ...config import PottoSettings
from ...db.queries.auth import get_user, get_user_by_username


class LocalAdminAuthProvider(AuthProvider):

    def __init__(self, settings: PottoSettings) -> None:
        super().__init__()
        self._settings = settings

    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        async with self._settings.get_db_session_maker()() as session:
            db_user = await get_user_by_username(session, username)
        if (
            db_user is None
            or not db_user.is_active
            or db_user.hashed_password is None
            or not bcrypt.checkpw(password.encode(), db_user.hashed_password.encode())
        ):
            raise LoginFailed("Invalid credentials")
        request.session["user_id"] = str(db_user.id)
        return response

    async def is_authenticated(self, request: Request) -> bool:
        return await _check_session(request, self._settings)

    def get_admin_user(self, request: Request) -> AdminUser | None:
        return _get_admin_user(request)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response


class OIDCAdminAuthProvider(AuthProvider):

    def __init__(self, settings: PottoSettings) -> None:
        super().__init__()
        self._settings = settings

    async def render_login(self, request: Request, admin) -> Response:
        """Skip the login form and redirect straight to the OIDC provider."""
        base_url = str(request.base_url).rstrip("/")
        next_url = base_url + "/admin"
        return RedirectResponse(f"{base_url}/auth/oidc/login?next={next_url}")

    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        # Not used – login is handled by the OIDC redirect flow
        raise LoginFailed("Use OIDC login")

    async def is_authenticated(self, request: Request) -> bool:
        return await _check_session(request, self._settings)

    def get_admin_user(self, request: Request) -> AdminUser | None:
        return _get_admin_user(request)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response


async def _check_session(request: Request, settings: PottoSettings) -> bool:
    user_id = request.session.get("user_id")
    if not user_id:
        return False
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return False
    async with settings.get_db_session_maker()() as session:
        db_user = await get_user(session, uid)
    if db_user is None or not db_user.is_active:
        return False
    request.state.admin_db_user = db_user
    return True


def _get_admin_user(request: Request) -> AdminUser | None:
    db_user = getattr(request.state, "admin_db_user", None)
    if db_user is None:
        return None
    return AdminUser(username=db_user.username)
