from fastapi import (
    APIRouter,
    Request,
)

from .... import constants
from ....schemas.web.landing import JsonLanding
from ....wrapper import Potto

router = APIRouter()


@router.get("/", name="landing-page", response_model_exclude_none=True)
async def landing_page(request: Request) -> JsonLanding:
    potto: Potto = request.state.potto
    result = await potto.api_get_landing_page(
        locale=request.state.locale,
        output_format=constants.PYGEOAPI_F_JSON
    )
    return JsonLanding.from_potto(result, request.url_for)