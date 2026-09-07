import logging
from typing import Annotated

import pydantic
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from fastapi.security import OAuth2PasswordRequestForm

from .. import responses
from ....authn.jwt import create_access_token
from ..dependencies import SettingsDependency

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginResponse(pydantic.BaseModel):
    access_token: str
    token_type: str = "bearer"


# security: [{}] marks this as intentionally public; security: [] is treated the same
# as "undefined" by the OWASP spectral rule (check-security.js line 68).
@router.post(
    "/login",
    name="login",
    openapi_extra={"security": [{}]},
    responses=responses.ERROR_RESPONSES,
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: SettingsDependency,
) -> LoginResponse:
    """Authenticate with username and password, receive a JWT access token."""
    user = await settings.get_user_account_manager().authenticate(
        form_data.username, form_data.password
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(
        user,
        settings.session_secret_key.get_secret_value(),
    )
    return LoginResponse(access_token=token)
