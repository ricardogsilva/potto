import logging

from starlette.requests import Request
from starlette.responses import Response

from ...wrapper import Potto
from ...schemas import auth as auth_schemas

logger = logging.getLogger(__name__)


async def get_landing_page(request: Request) -> Response:
    user = (
        potto_user
        if isinstance(
            (potto_user := request.user), auth_schemas.PottoUser)
        else None
    )
    potto: Potto = request.state.potto
    return request.state.templates.TemplateResponse(
        request,
        "landing-page.html",
        context={
            "contents": await potto.api_get_landing_page(
                user=user,
                language=request.state.language
            ),
            "settings": request.state.settings,
            "user": user
        }
    )
