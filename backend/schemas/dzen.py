from typing import Optional

from pydantic import BaseModel, Field


class DzenParseRequest(BaseModel):
    channel_id: str = Field(..., min_length=1, description="ID канала Дзен")
    max_posts: int = Field(default=60, ge=1, le=500, description="Максимум постов для загрузки")
    save_csv: bool = Field(default=False, description="Сохранить результат в CSV")
    output_file: Optional[str] = Field(default=None, description="Имя CSV-файла (если save_csv=true)")


class DzenParsedPost(BaseModel):
    id: Optional[str] = None
    date: str = ""
    title: str = ""
    text: str = ""
    views: int = 0
    time_to_read_sec: int = 0
    link: str = ""
    comments_link: str = ""
    channel: str = ""


class DzenParseResponse(BaseModel):
    channel_title: str
    count: int
    saved_to: Optional[str] = None
    posts: list[DzenParsedPost]
