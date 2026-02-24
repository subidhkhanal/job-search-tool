import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..dependencies import get_current_user
from ..models.schemas import MarkScrapedJobRequest
from tracker import get_scraped_jobs, mark_scraped_job, save_scraped_job
from scraper import run_all_scrapers
from nightly import score_job, llm_rerank_jobs

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


@router.post("/run")
async def run_scrapers(_user: str = Depends(get_current_user)):
    async def generate():
        loop = asyncio.get_event_loop()

        yield f"data: {json.dumps({'event': 'started', 'message': 'Scraping all sources...'})}\n\n"

        jobs, sources_status, sources_errors = await loop.run_in_executor(
            None, run_all_scrapers
        )

        yield f"data: {json.dumps({'event': 'scrape_complete', 'sources_status': sources_status, 'sources_errors': {k: str(v) for k, v in (sources_errors or {}).items()}, 'total_jobs': len(jobs)})}\n\n"

        # Save scraped jobs to database
        for job in jobs:
            try:
                save_scraped_job(
                    title=job.get("title", ""),
                    company=job.get("company", ""),
                    location=job.get("location", ""),
                    source=job.get("source", ""),
                    url=job.get("url", ""),
                    description=job.get("description", ""),
                )
            except Exception:
                pass

        # Score jobs
        yield f"data: {json.dumps({'event': 'scoring', 'message': 'Scoring jobs...'})}\n\n"

        for job in jobs:
            job["score"] = score_job(job)
        jobs = [j for j in jobs if j["score"] > -100]
        jobs.sort(key=lambda j: j["score"], reverse=True)

        yield f"data: {json.dumps({'event': 'scoring_complete', 'jobs_count': len(jobs)})}\n\n"

        # LLM rerank top candidates
        yield f"data: {json.dumps({'event': 'reranking', 'message': 'LLM re-ranking top candidates...'})}\n\n"

        jobs = await loop.run_in_executor(None, llm_rerank_jobs, jobs, 20)
        top_jobs = [j for j in jobs if j.get("score", 0) >= 20][:20]

        # Detect work mode for each job
        for j in top_jobs:
            text = (
                j.get("location", "") + " " + j.get("description", "") + " " + j.get("title", "")
            ).lower()
            if any(kw in text for kw in ["onsite", "on-site", "on site", "in-office", "wfo"]):
                j["work_mode"] = "Onsite"
            elif "hybrid" in text:
                j["work_mode"] = "Hybrid"
            elif "remote" in text:
                j["work_mode"] = "Remote"
            else:
                j["work_mode"] = ""

        yield f"data: {json.dumps({'event': 'complete', 'jobs': top_jobs, 'total': len(jobs)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
