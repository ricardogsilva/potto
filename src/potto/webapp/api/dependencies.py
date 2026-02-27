from typing import (
    Annotated,
    Iterator,
)

from fastapi import Depends

from ... import config
from ...wrapper import Potto


def get_settings() -> Iterator[config.PottoSettings]:
    yield config.get_settings()


def get_potto(
        settings: Annotated[config.PottoSettings, Depends(get_settings)]
) -> Iterator[Potto]:
    yield Potto(settings)

PottoDependency = Annotated[Potto, Depends(get_potto)]
