from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..models.schemas import MarkScrapedJobRequest
from tracker import get_scraped_jobs, mark_scraped_job

router = APIRouter()


@router.get("")
def list_scraped_jobs(
    source: str | None = None,
    _user: str = Depends(get_current_user),
):
    df = get_scraped_jobs(source=source)
    return df.to_dict("records") if not df.empty else []


@router.patch("/{job_id}")
def mark_job(
    job_id: int,
    body: MarkScrapedJobRequest,
    _user: str = Depends(get_current_user),
):
    mark_scraped_job(job_id, body.action)
    return {"success": True}
