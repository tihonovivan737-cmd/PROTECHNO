from fastapi import APIRouter, HTTPException, status

from backend.modules.profiles.registry import get_profile, list_profiles
from backend.schemas.profiles import ProfileResponse

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("/", response_model=list[ProfileResponse])
def get_all_profiles() -> list[ProfileResponse]:
    return [ProfileResponse.from_profile(p) for p in list_profiles()]


@router.get("/{name}", response_model=ProfileResponse)
def get_profile_by_name(name: str) -> ProfileResponse:
    profile = get_profile(name)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Профиль '{name}' не найден",
        )
    return ProfileResponse.from_profile(profile)
