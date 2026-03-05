from fastapi import APIRouter

from ..models.schemas import PushSubscriptionRequest
from tracker import (
    get_notifications,
    get_unread_count,
    mark_notification_read,
    mark_all_notifications_read,
    save_push_subscription,
    delete_push_subscription,
)

router = APIRouter()


@router.get("")
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
):
    return get_notifications(unread_only=unread_only, limit=limit)


@router.get("/unread-count")
def unread_count():
    return {"count": get_unread_count()}


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: int,
):
    mark_notification_read(notification_id)
    return {"success": True}


@router.post("/mark-all-read")
def mark_all_read():
    mark_all_notifications_read()
    return {"success": True}


@router.post("/push/subscribe")
def subscribe_push(
    data: PushSubscriptionRequest,
):
    save_push_subscription(
        endpoint=data.endpoint,
        keys_p256dh=data.keys.get("p256dh", ""),
        keys_auth=data.keys.get("auth", ""),
    )
    return {"success": True}


@router.post("/push/unsubscribe")
def unsubscribe_push(
    data: PushSubscriptionRequest,
):
    delete_push_subscription(endpoint=data.endpoint)
    return {"success": True}
