from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreatePostRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Текст поста")
    attachments: Optional[str] = Field(
        None, description="Вложения VK, например 'photo123_456'"
    )
    from_group: bool = Field(True, description="Публиковать от имени сообщества")


class CreatePostResponse(BaseModel):
    post_id: int
    url: str


class ParsePostsRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=1,
        description=(
            "Ссылка на VK-сообщество. Поддерживается короткое имя ('svoedelomc'), "
            "'vk.com/<domain>', 'https://vk.com/<domain>', 'https://vk.com/club123', "
            "'https://vk.com/public123'."
        ),
    )
    max_posts: Optional[int] = Field(
        None, gt=0, description="Сколько постов выгрузить максимум."
    )


class ParsedPost(BaseModel):
    id: int
    date: datetime
    text: str
    likes: int
    reposts: int
    comments: int
    views: int


class ParsePostsResponse(BaseModel):
    domain: str
    count: int
    posts: list[ParsedPost]
