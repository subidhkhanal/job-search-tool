from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from tracker import (
    get_follow_ups_due,
    get_platform_effectiveness,
    get_role_analysis,
    get_stats,
    get_status_funnel,
    get_weekly_trend,
)

router = APIRouter()


@router.get("/dashboard")
def dashboard_stats(_user: str = Depends(get_current_user)):
    return get_stats()


@router.get("/follow-ups")
def follow_ups(_user: str = Depends(get_current_user)):
    df = get_follow_ups_due()
    return df.to_dict("records") if not df.empty else []


@router.get("/weekly-trend")
def weekly_trend(_user: str = Depends(get_current_user)):
    df = get_weekly_trend()
    return df.to_dict("records") if not df.empty else []


@router.get("/platform-effectiveness")
def platform_effectiveness(_user: str = Depends(get_current_user)):
    df = get_platform_effectiveness()
    return df.to_dict("records") if not df.empty else []


@router.get("/status-funnel")
def status_funnel(_user: str = Depends(get_current_user)):
    return get_status_funnel()


@router.get("/role-analysis")
def role_analysis(_user: str = Depends(get_current_user)):
    df = get_role_analysis()
    return df.to_dict("records") if not df.empty else []
