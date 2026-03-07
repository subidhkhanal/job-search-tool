from fastapi import APIRouter, Query
from typing import Optional

from ..models.schemas import LogFollowUpRequest, UpdateFollowUpOutcomeRequest
from tracker import (
    log_follow_up,
    get_follow_up_history,
    update_follow_up_outcome,
    update_status,
    update_referral_status,
    get_follow_up_effectiveness,
)

router = APIRouter()


@router.post("/log")
def log_follow_up_sent(body: LogFollowUpRequest):
    follow_up_number = log_follow_up(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        message_content=body.message_content,
        channel=body.channel,
    )
    if body.entity_type == "application":
        update_status(body.entity_id, "Follow-up Sent")
    elif body.entity_type == "referral":
        update_referral_status(body.entity_id, "Contacted")
    return {"success": True, "follow_up_number": follow_up_number}


@router.get("/history")
def follow_up_history(
    entity_type: str = Query(...),
    entity_id: int = Query(...),
):
    records = get_follow_up_history(entity_type, entity_id)
    return records


@router.patch("/{history_id}/outcome")
def patch_outcome(history_id: int, body: UpdateFollowUpOutcomeRequest):
    update_follow_up_outcome(history_id, body.outcome)
    return {"success": True}


@router.get("/effectiveness")
def effectiveness():
    return get_follow_up_effectiveness()
