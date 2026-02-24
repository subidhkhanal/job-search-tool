from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..models.schemas import CompanyResearchRequest
from company_research import research_company
from tracker import get_cached_research, save_research_cache

router = APIRouter()


@router.post("")
def research(
    body: CompanyResearchRequest,
    _user: str = Depends(get_current_user),
):
    cached = get_cached_research(body.company_name)
    if cached:
        return cached

    result = research_company(body.company_name)
    if result.get("description"):
        save_research_cache(body.company_name, result)

    return result
