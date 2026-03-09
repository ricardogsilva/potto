import uuid

import bcrypt
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed

from ...config import PottoSettings
from ...db.queries.auth import get_user, get_user_by_username


class PottoAdminAuthProvider(AuthProvider):

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
        user_id = request.session.get("user_id")
        if not user_id:
            return False
        try:
            uid = uuid.UUID(user_id)
        except (ValueError, TypeError):
            return False
        async with self._settings.get_db_session_maker()() as session:
            db_user = await get_user(session, uid)
        if db_user is None or not db_user.is_active:
            return False
        request.state.admin_db_user = db_user
        return True

    def get_admin_user(self, request: Request) -> AdminUser | None:
        db_user = getattr(request.state, "admin_db_user", None)
        if db_user is None:
            return None
        return AdminUser(username=db_user.username)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response
