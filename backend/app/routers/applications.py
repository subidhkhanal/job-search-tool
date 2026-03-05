from fastapi import APIRouter, Query
from typing import Optional

from ..models.schemas import AddApplicationRequest, UpdateStatusRequest, UpdateNotesRequest
from tracker import (
    add_application,
    delete_application,
    get_all_applications,
    update_status,
    update_notes,
)

router = APIRouter()


@router.get("")
def list_applications(
    status_filter: Optional[str] = Query(None, alias="status"),
    type_filter: Optional[str] = Query(None, alias="type"),
    platform: Optional[str] = None,

):
    df = get_all_applications()
    if df.empty:
        return []
    if status_filter:
        df = df[df["status"] == status_filter]
    if type_filter:
        df = df[df["type"] == type_filter]
    if platform:
        df = df[df["platform"] == platform]
    return df.to_dict("records")


@router.post("")
def create_application(
    body: AddApplicationRequest,

):
    add_application(
        company=body.company,
        role=body.role,
        job_type=body.job_type,
        platform=body.platform,
        url=body.url,
        noc_compatible=body.noc_compatible,
        conversion=body.conversion,
        salary=body.salary,
        notes=body.notes,
    )
    return {"success": True}


@router.patch("/{app_id}/status")
def patch_status(
    app_id: int,
    body: UpdateStatusRequest,

):
    update_status(app_id, body.status)
    return {"success": True}


@router.patch("/{app_id}/notes")
def patch_notes(
    app_id: int,
    body: UpdateNotesRequest,

):
    update_notes(app_id, body.notes)
    return {"success": True}


@router.delete("/{app_id}")
def remove_application(
    app_id: int,

):
    delete_application(app_id)
    return {"success": True}
