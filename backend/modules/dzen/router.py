from fastapi import APIRouter, HTTPException, status

from backend.modules.dzen import service
from backend.schemas.dzen import (
    DzenParseRequest,
    DzenParseResponse,
    DzenParsedPost,
)

router = APIRouter(prefix="/api/dzen_parser", tags=["dzen_parser"])

DEFAULT_OUTPUT = "dzen_posts.csv"


@router.post("/parse", response_model=DzenParseResponse)
def parse_dzen_channel(payload: DzenParseRequest) -> DzenParseResponse:
    try:
        raw_items, channel_title = service.fetch_channel_posts(
            channel_id=payload.channel_id,
            max_posts=payload.max_posts,
        )
    except service.DzenParserError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка парсинга Дзен: {e}",
        )

    parsed = [service.parse_post(item, channel_title) for item in raw_items]

    saved_to = None
    if payload.save_csv and parsed:
        output = payload.output_file or DEFAULT_OUTPUT
        service.save_to_csv(raw_items, output, channel_title)
        saved_to = output

    return DzenParseResponse(
        channel_title=channel_title,
        count=len(parsed),
        saved_to=saved_to,
        posts=[DzenParsedPost(**p) for p in parsed],
    )
