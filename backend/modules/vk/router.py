from fastapi import APIRouter, HTTPException, status

from backend.modules.vk import service
from backend.schemas.vk import (
    CreatePostRequest,
    CreatePostResponse,
    ParsePostsRequest,
    ParsePostsResponse,
    ParsedPost,
)

router = APIRouter(prefix="/api/vk", tags=["vk"])


@router.post("/parse", response_model=ParsePostsResponse)
def parse_wall(payload: ParsePostsRequest) -> ParsePostsResponse:
    try:
        raw, domain_label = service.fetch_posts(
            url=payload.url,
            max_posts=payload.max_posts,
        )
    except service.InvalidVKUrlError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except service.VKAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    parsed = [service.parse_post(p) for p in raw]
    return ParsePostsResponse(
        domain=domain_label,
        count=len(parsed),
        posts=[ParsedPost(**p) for p in parsed],
    )


@router.post(
    "/poster",
    response_model=CreatePostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(payload: CreatePostRequest) -> CreatePostResponse:
    try:
        post_id = service.create_post(
            message=payload.message,
            attachments=payload.attachments,
            from_group=payload.from_group,
        )
    except service.VKAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    return CreatePostResponse(post_id=post_id, url=service.post_url(post_id))
