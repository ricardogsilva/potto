from typing import TypedDict

from starlette.templating import Jinja2Templates

from .. import config
from ..authn.oidc import OIDCProvider
from ..authz.base import AuthorizationBackendProtocol
from ..wrapper import Potto


class AppState(TypedDict):
    settings: config.PottoSettings
    potto: Potto
    templates: Jinja2Templates
    oidc_provider: OIDCProvider | None
    authorization_backend: AuthorizationBackendProtocol
