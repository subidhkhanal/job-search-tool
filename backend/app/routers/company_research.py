from fastapi import APIRouter

from ..models.schemas import CompanyResearchRequest
from company_research import research_company
from tracker import get_cached_research, save_research_cache

router = APIRouter()


@router.post("")
def research(
    body: CompanyResearchRequest,
):
    cached = get_cached_research(body.company_name)
    if cached:
        return cached

    result = research_company(body.company_name)
    if result.get("description"):
        save_research_cache(body.company_name, result)

    return result
