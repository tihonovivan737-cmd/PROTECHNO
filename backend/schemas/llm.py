from typing import Optional

from pydantic import BaseModel, Field


class GeneratePostRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Краткое описание события")
    profile: Optional[str] = Field(
        default=None,
        description="Имя профиля площадки (volunteers, youth_center). По умолчанию — youth_center",
    )
    state: Optional[str] = Field(
        default=None,
        description="Состояние сообщества: CRISIS, NORMAL или RISE",
    )


class GeneratePostResponse(BaseModel):
    text: str
    model: str
    shots_used: int
    profile_used: Optional[str] = None
