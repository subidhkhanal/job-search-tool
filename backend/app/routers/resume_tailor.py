from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI

from ..dependencies import get_openai_client
from ..models.schemas import ResumeTailorRequest
from resume_tailor import tailor_resume

router = APIRouter()


@router.post("")
def tailor_resume_endpoint(
    body: ResumeTailorRequest,
    client: OpenAI = Depends(get_openai_client),
):
    try:
        return tailor_resume(client, body.title, body.jd_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
