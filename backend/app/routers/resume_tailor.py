from fastapi import APIRouter, Depends
from groq import Groq

from ..dependencies import get_current_user, get_groq_client
from ..models.schemas import ResumeTailorRequest
from resume_tailor import (
    analyze_gaps,
    generate_summary_lines,
    suggest_project_order,
    suggest_skill_order,
)

router = APIRouter()


@router.post("")
def tailor_resume(
    body: ResumeTailorRequest,
    client: Groq = Depends(get_groq_client),
    _user: str = Depends(get_current_user),
):
    projects = suggest_project_order(body.jd_text)
    skills = suggest_skill_order(body.jd_text)
    gaps = analyze_gaps(body.jd_text)
    summaries = generate_summary_lines(client, body.title, body.jd_text)

    return {
        "projects": projects,
        "skills": skills,
        "gaps": gaps,
        "summaries": summaries,
    }
