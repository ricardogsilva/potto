import logging
import uuid

import jwt
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
)
from starlette.requests import HTTPConnection

from ..config import PottoSettings
from ..db.queries.auth import get_user, get_user_by_oidc_sub
from ..schemas.auth import PottoUser
from .jwt import decode_access_token
from .oidc import OIDCProvider

logger = logging.getLogger(__name__)


class LocalAuthBackend(AuthenticationBackend):

    def __init__(self, settings: PottoSettings) -> None:
        self._settings = settings

    async def authenticate(
            self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, PottoUser] | None:
        # Try session first
        user_id = conn.session.get("user_id")
        if user_id:
            potto_user = await self._get_user_from_db(user_id)
            if potto_user is not None:
                return AuthCredentials(potto_user.scopes), potto_user
            logger.warning(
                f"Session contains user_id {user_id!r} but user not found or inactive"
            )

        # Try local HS256 Bearer JWT
        auth_header = conn.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_access_token(
                    token,
                    self._settings.session_secret_key.get_secret_value(),
                )
            except jwt.InvalidTokenError:
                return None
            potto_user = await self._get_user_from_db(payload["sub"])
            if potto_user is not None:
                return AuthCredentials(potto_user.scopes), potto_user
            logger.warning(
                f"JWT contains sub {payload['sub']!r} but user not found or inactive"
            )

        return None

    async def _get_user_from_db(self, user_id: str) -> PottoUser | None:
        try:
            uid = uuid.UUID(user_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user_id format: {user_id!r}")
            return None
        async with self._settings.get_db_session_maker()() as session:
            db_user = await get_user(session, uid)
        if db_user is None:
            logger.debug(f"User {uid} not found in database")
            return None
        if not db_user.is_active:
            logger.warning(f"User {db_user.username!r} is inactive, denying access")
            return None
        return db_user.to_potto()


class OIDCAuthBackend(AuthenticationBackend):

    def __init__(self, settings: PottoSettings, oidc_provider: OIDCProvider) -> None:
        self._settings = settings
        self._oidc_provider = oidc_provider

    async def authenticate(
            self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, PottoUser] | None:
        # Try session first (set during OIDC callback)
        user_id = conn.session.get("user_id")
        if user_id:
            potto_user = await self._get_user_from_db(user_id)
            if potto_user is not None:
                return AuthCredentials(potto_user.scopes), potto_user
            logger.warning(
                f"Session contains user_id {user_id!r} but user not found or inactive"
            )

        # Try OIDC RS256 Bearer JWT
        auth_header = conn.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                claims = await self._oidc_provider.validate_access_token(token)
            except jwt.InvalidTokenError:
                return None
            async with self._settings.get_db_session_maker()() as session:
                db_user = await get_user_by_oidc_sub(session, claims["sub"])
                if db_user is None:
                    db_user = await self._oidc_provider.provision_user(session, claims)
            if not db_user.is_active:
                logger.warning(
                    f"User {db_user.username!r} is inactive, denying access"
                )
                return None
            # When roles_claim is configured, scopes come from the token directly
            scopes = self._oidc_provider.extract_scopes(claims) or db_user.scopes
            potto_user = PottoUser(
                id=db_user.id,
                username=db_user.username,
                email=db_user.email,
                is_active=db_user.is_active,
                scopes=scopes,
            )
            return AuthCredentials(potto_user.scopes), potto_user

        return None

    async def _get_user_from_db(self, user_id: str) -> PottoUser | None:
        try:
            uid = uuid.UUID(user_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user_id format: {user_id!r}")
            return None
        async with self._settings.get_db_session_maker()() as session:
            db_user = await get_user(session, uid)
        if db_user is None:
            logger.debug(f"User {uid} not found in database")
            return None
        if not db_user.is_active:
            logger.warning(f"User {db_user.username!r} is inactive, denying access")
            return None
        return db_user.to_potto()
