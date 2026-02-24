from fastapi import APIRouter, Depends, Query

from ..dependencies import get_current_user
from ..models.schemas import AddDemoRequest, UpdateDemoRequest
from tracker import add_mini_demo, get_active_demos, get_demo_results, update_mini_demo

router = APIRouter()


@router.get("")
def list_demos(
    active_only: bool = Query(True),
    _user: str = Depends(get_current_user),
):
    df = get_active_demos() if active_only else get_demo_results()
    return df.to_dict("records") if not df.empty else []


@router.post("")
def create_demo(
    body: AddDemoRequest,
    _user: str = Depends(get_current_user),
):
    add_mini_demo(body.company, body.role, body.demo_idea)
    return {"success": True}


@router.patch("/{demo_id}")
def patch_demo(
    demo_id: int,
    body: UpdateDemoRequest,
    _user: str = Depends(get_current_user),
):
    updates = body.model_dump(exclude_none=True)
    if updates:
        update_mini_demo(demo_id, **updates)
    return {"success": True}
