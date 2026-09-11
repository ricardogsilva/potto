import logging

import jwt
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
)
from starlette.requests import HTTPConnection

from ..config import PottoSettings
from ..schemas.auth import PottoUser
from ._shared import get_authn_system_user
from .jwt import decode_access_token
from .oidc import OIDCProvider

logger = logging.getLogger(__name__)


class LocalAuthBackend(AuthenticationBackend):
    _settings: PottoSettings

    def __init__(self, settings: PottoSettings) -> None:
        self._settings = settings

    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, PottoUser] | None:
        if user_id := conn.session.get("user_id"):
            logger.debug(f"{user_id=} found in the session")
            if (potto_user := await self._get_user_from_db(user_id)) is not None:
                return AuthCredentials(potto_user.scopes), potto_user
            logger.warning(
                f"Session contains user_id {user_id!r} but user not found or inactive"
            )
        # Try local HS256 Bearer JWT
        if (
            auth_header := conn.headers.get("Authorization")
        ) and auth_header.startswith("Bearer "):
            token = auth_header.rpartition(" ")[-1]
            try:
                payload = decode_access_token(
                    token,
                    self._settings.session_secret_key.get_secret_value(),
                )
            except jwt.InvalidTokenError:
                logger.warning(f"Was sent invalid token {token!r}")
                return None
            if (potto_user := await self._get_user_from_db(payload["sub"])) is not None:
                return AuthCredentials(potto_user.scopes), potto_user
            logger.warning(
                f"JWT contains sub {payload['sub']!r} but user not found or inactive"
            )

        return None

    async def _get_user_from_db(self, user_id: str) -> PottoUser | None:
        user = await self._settings.get_user_account_manager().get_user(
            user_id, get_authn_system_user()
        )
        if user is None:
            logger.debug(f"User {user_id!r} not found in database")
            return None
        if not user.is_active:
            logger.warning(f"User {user.username!r} is inactive, denying access")
            return None
        return user


class OIDCAuthBackend(AuthenticationBackend):
    _settings: PottoSettings
    _oidc_provider: OIDCProvider

    def __init__(self, settings: PottoSettings, oidc_provider: OIDCProvider) -> None:
        self._settings = settings
        self._oidc_provider = oidc_provider

    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, PottoUser] | None:
        # Try session first (set during OIDC callback)
        if user_id := conn.session.get("user_id"):
            potto_user = await self._get_user_from_db(user_id)
            if potto_user is not None:
                return AuthCredentials(potto_user.scopes), potto_user
            logger.warning(
                f"Session contains user_id {user_id!r} but user not found or inactive"
            )

        # Try OIDC RS256 Bearer JWT
        if (
            auth_header := conn.headers.get("Authorization")
        ) and auth_header.startswith("Bearer "):
            token = auth_header.rpartition(" ")[-1]
            try:
                claims = await self._oidc_provider.validate_access_token(token)
            except jwt.InvalidTokenError:
                return None
            user_account_manager = self._settings.get_user_account_manager()
            user = await user_account_manager.get_user(
                claims["sub"], get_authn_system_user()
            )
            if user is None:
                user = await self._oidc_provider.provision_user(self._settings, claims)
            if not user.is_active:
                logger.warning(f"User {user.username!r} is inactive, denying access")
                return None
            # When roles_claim is configured, scopes come from the token directly
            scopes = self._oidc_provider.extract_scopes(claims) or user.scopes
            potto_user = PottoUser(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                scopes=scopes,
            )
            return AuthCredentials(potto_user.scopes), potto_user

        return None

    async def _get_user_from_db(self, user_id: str) -> PottoUser | None:
        user = await self._settings.get_user_account_manager().get_user(
            user_id, get_authn_system_user()
        )
        if user is None:
            logger.debug(f"User {user_id!r} not found in database")
            return None
        if not user.is_active:
            logger.warning(f"User {user.username!r} is inactive, denying access")
            return None
        return user
