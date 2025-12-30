from typing import TypedDict

from starlette.templating import Jinja2Templates

from .. import config
from ..wrapper import Potto


class AppState(TypedDict):
    settings: config.PottoSettings
    potto: Potto
    templates: Jinja2Templates
