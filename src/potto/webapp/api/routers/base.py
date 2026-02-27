from fastapi import (
    APIRouter,
    Request,
)

from ....schemas.web import base

from ..dependencies import PottoDependency

router = APIRouter()



@router.get("/", name="landing-page", response_model_exclude_none=True)
async def landing_page(request: Request, potto: PottoDependency) -> base.JsonLanding:
    result = await potto.api_get_landing_page(language=request.state.locale.language)
    return base.JsonLanding.from_potto(result, request.url_for)


@router.get("/conformance", name="conformance-page")
async def conformance_page(potto: PottoDependency) -> base.JsonConformance:
    result = await potto.api_get_conformance_details()
    return base.JsonConformance(conformsTo=result.conforms_to)
