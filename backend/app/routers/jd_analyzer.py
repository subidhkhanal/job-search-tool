from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..models.schemas import ATSCheckRequest, FullAnalyzeRequest
from jd_analyzer import ats_check, full_analyze, _get_default_resume_text
from company_research import research_company
from tracker import get_cached_research, save_research_cache

router = APIRouter()


@router.post("/full")
def full_analysis(
    body: FullAnalyzeRequest,
    _user: str = Depends(get_current_user),
):
    result = full_analyze(body.title, body.description)

    # ATS check
    resume = body.custom_resume or _get_default_resume_text()
    ats = ats_check(resume, body.description)
    result["ats"] = ats

    # Company research (optional)
    company_intel = None
    if body.company:
        cached = get_cached_research(body.company)
        if cached:
            company_intel = cached
        else:
            company_intel = research_company(body.company)
            if company_intel.get("description"):
                save_research_cache(body.company, company_intel)
        result["company_intel"] = company_intel

    return result


@router.post("/ats")
def ats_only(
    body: ATSCheckRequest,
    _user: str = Depends(get_current_user),
):
    resume = body.custom_resume or _get_default_resume_text()
    return ats_check(resume, body.jd_text)
