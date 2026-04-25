from backend.schemas.vk import (
    CreatePostRequest,
    CreatePostResponse,
    ParsePostsRequest,
    ParsePostsResponse,
    ParsedPost,
)
from backend.schemas.llm import (
    GeneratePostRequest,
    GeneratePostResponse,
)

__all__ = [
    "CreatePostRequest",
    "CreatePostResponse",
    "ParsePostsRequest",
    "ParsePostsResponse",
    "ParsedPost",
    "GeneratePostRequest",
    "GeneratePostResponse",
]
