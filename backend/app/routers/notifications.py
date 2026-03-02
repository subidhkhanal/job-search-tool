from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from tracker import (
    get_notifications,
    get_unread_count,
    mark_notification_read,
    mark_all_notifications_read,
)

router = APIRouter()


@router.get("")
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    _user: str = Depends(get_current_user),
):
    return get_notifications(unread_only=unread_only, limit=limit)


@router.get("/unread-count")
def unread_count(_user: str = Depends(get_current_user)):
    return {"count": get_unread_count()}


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: int,
    _user: str = Depends(get_current_user),
):
    mark_notification_read(notification_id)
    return {"success": True}


@router.post("/mark-all-read")
def mark_all_read(_user: str = Depends(get_current_user)):
    mark_all_notifications_read()
    return {"success": True}
