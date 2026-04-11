from typing import (
    Annotated,
    Iterator,
)

import babel
import pydantic
from fastapi import (
    Depends,
    Query,
    Request,
)

from ... import config
from ...authz.base import AuthorizationBackendProtocol
from ...schemas.auth import PottoUser
from ...schemas.potto import Pagination
from ...wrapper import Potto


def get_settings() -> Iterator[config.PottoSettings]:
    yield config.get_settings()


def get_potto(
        settings: Annotated[config.PottoSettings, Depends(get_settings)]
) -> Iterator[Potto]:
    yield Potto(settings)


def get_current_user(request: Request) -> PottoUser | None:
    return request.user if isinstance(request.user, PottoUser) else None


def get_current_locale(request: Request) -> babel.Locale:
    return babel.Locale.parse(request.state.language)


def get_authorization_backend(
        settings: Annotated[config.PottoSettings, Depends(get_settings)]
) -> AuthorizationBackendProtocol:
    return settings.get_authorization_backend()


def get_pagination_limit(
        settings: Annotated[config.PottoSettings, Depends(get_settings)],
        limit: Annotated[int | None, Query(gte=1)] = None
) -> int:
    return min(limit or 1, settings.max_page_size)


SettingsDependency = Annotated[config.PottoSettings, Depends(get_settings)]
PottoDependency = Annotated[Potto, Depends(get_potto)]
UserDependency = Annotated[PottoUser | None, Depends(get_current_user)]
LocaleDependency = Annotated[babel.Locale, Depends(get_current_locale)]
AuthorizationBackendDependency = Annotated[
    AuthorizationBackendProtocol, Depends(get_authorization_backend)
]
PaginationLimitDependency = Annotated[int, Depends(get_pagination_limit)]
