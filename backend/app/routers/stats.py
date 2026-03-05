from fastapi import APIRouter

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
def dashboard_stats():
    return get_stats()


@router.get("/follow-ups")
def follow_ups():
    df = get_follow_ups_due()
    return df.to_dict("records") if not df.empty else []


@router.get("/weekly-trend")
def weekly_trend():
    df = get_weekly_trend()
    return df.to_dict("records") if not df.empty else []


@router.get("/platform-effectiveness")
def platform_effectiveness():
    df = get_platform_effectiveness()
    return df.to_dict("records") if not df.empty else []


@router.get("/status-funnel")
def status_funnel():
    return get_status_funnel()


@router.get("/role-analysis")
def role_analysis():
    df = get_role_analysis()
    return df.to_dict("records") if not df.empty else []
