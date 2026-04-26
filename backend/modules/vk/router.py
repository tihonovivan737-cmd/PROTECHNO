from fastapi import APIRouter, HTTPException, UploadFile, File, status

from backend.modules.vk import service
from backend.schemas.vk import (
    CreatePostRequest,
    CreatePostResponse,
    DeletePostRequest,
    DeletePostResponse,
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


@router.post("/delete", response_model=DeletePostResponse)
def delete_post(payload: DeletePostRequest) -> DeletePostResponse:
    try:
        success = service.delete_post(payload.post_id)
    except service.VKAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    return DeletePostResponse(success=success)


@router.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    """Загружает фото в VK и возвращает строку вложения (photo{owner}_{id})."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужен файл изображения")
    try:
        file_bytes = await file.read()
        attachment = service.upload_wall_photo(file_bytes, file.filename or "photo.jpg", file.content_type)
    except service.VKAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    return {"attachment": attachment}
