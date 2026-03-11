from typing import (
    Annotated,
    Iterator,
)

import babel
from fastapi import Depends, Request

from ... import config
from ...schemas.auth import PottoUser
from ...wrapper import Potto


def get_settings() -> Iterator[config.PottoSettings]:
    yield config.get_settings()


def get_potto(
        settings: Annotated[config.PottoSettings, Depends(get_settings)]
) -> Iterator[Potto]:
    yield Potto(settings)


def get_current_user(request: Request) -> PottoUser:
    return request.user


def get_current_locale(request: Request) -> babel.Locale:
    return babel.Locale.parse(request.state.language)


SettingsDependency = Annotated[config.PottoSettings, Depends(get_settings)]
PottoDependency = Annotated[Potto, Depends(get_potto)]
UserDependency = Annotated[PottoUser, Depends(get_current_user)]
LocaleDependency = Annotated[babel.Locale, Depends(get_current_locale)]
