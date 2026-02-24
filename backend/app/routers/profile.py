from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..models.schemas import UserProfileRequest, UserProfileResponse
from profile import get_profile, upsert_profile

router = APIRouter()


@router.get("/", response_model=UserProfileResponse)
def read_profile(_user: str = Depends(get_current_user)):
    data = get_profile(_user)
    if data is None:
        # Return empty profile shell
        return UserProfileResponse(username=_user)
    return UserProfileResponse(**data)


@router.put("/", response_model=UserProfileResponse)
def update_profile(body: UserProfileRequest, _user: str = Depends(get_current_user)):
    payload = body.model_dump(exclude_none=True)
    saved = upsert_profile(_user, payload)
    if saved:
        return UserProfileResponse(**saved)
    return UserProfileResponse(username=_user)
