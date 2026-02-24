from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from tracker import get_email_logs, get_email_log

router = APIRouter()


@router.get("/emails")
def list_email_logs(
    limit: int = 20,
    _user: str = Depends(get_current_user),
):
    """Get recent email logs (same content sent via email), newest first."""
    return get_email_logs(limit=limit)


@router.get("/emails/{log_id}")
def get_single_email_log(
    log_id: int,
    _user: str = Depends(get_current_user),
):
    """Get a single email log by ID."""
    log = get_email_log(log_id)
    if not log:
        return {"error": "Email log not found"}
    return log
