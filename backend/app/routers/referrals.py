from fastapi import APIRouter, Depends, Query
from typing import Optional

from ..dependencies import get_current_user
from ..models.schemas import AddReferralRequest, UpdateReferralStatusRequest
from tracker import (
    add_referral,
    get_referral_follow_ups_due,
    get_referral_stats,
    get_referrals_by_company,
    update_referral_status,
)

router = APIRouter()


@router.get("")
def list_referrals(
    company: Optional[str] = Query(None),
    _user: str = Depends(get_current_user),
):
    if company:
        df = get_referrals_by_company(company)
    else:
        from tracker import _get_client
        db = _get_client()
        resp = db.table("referrals").select("*").order("follow_up_date", desc=False).execute()
        import pandas as pd
        df = pd.DataFrame(resp.data)
    return df.to_dict("records") if not df.empty else []


@router.post("")
def create_referral(
    body: AddReferralRequest,
    _user: str = Depends(get_current_user),
):
    add_referral(
        contact_name=body.contact_name,
        company=body.company,
        contact_role=body.contact_role,
        relationship=body.relationship,
        linkedin_url=body.linkedin_url,
        email=body.email,
        notes=body.notes,
    )
    return {"success": True}


@router.patch("/{referral_id}/status")
def patch_referral_status(
    referral_id: int,
    body: UpdateReferralStatusRequest,
    _user: str = Depends(get_current_user),
):
    update_referral_status(referral_id, body.status)
    return {"success": True}


@router.get("/stats")
def referral_statistics(_user: str = Depends(get_current_user)):
    return get_referral_stats()


@router.get("/follow-ups")
def referral_follow_ups(_user: str = Depends(get_current_user)):
    df = get_referral_follow_ups_due()
    return df.to_dict("records") if not df.empty else []
