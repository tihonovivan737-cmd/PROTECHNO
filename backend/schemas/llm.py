from typing import Optional

from pydantic import BaseModel, Field


class GeneratePostRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Краткое описание события")


class GeneratePostResponse(BaseModel):
    text: str
    model: str
    shots_used: int
