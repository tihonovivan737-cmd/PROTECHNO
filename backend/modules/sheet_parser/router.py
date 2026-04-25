from fastapi import APIRouter, HTTPException, status

from backend.app.config import settings
from backend.modules.sheet_parser import service
from backend.schemas.sheet_parser import SheetParseRequest, SheetParseResponse

router = APIRouter(prefix="/api/sheet_parser", tags=["sheet_parser"])


@router.post("/parse", response_model=SheetParseResponse)
def parse_google_sheet(payload: SheetParseRequest) -> SheetParseResponse:
    sheet_id = payload.sheet_id or settings.GOOGLE_SHEET_ID
    gid = payload.gid if payload.gid is not None else str(settings.GOOGLE_SHEET_GID)

    if not sheet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан sheet_id и не задан GOOGLE_SHEET_ID в .env",
        )

    try:
        text = service.fetch_sheet_csv(sheet_id, gid)
    except service.SheetParserError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

    rows = service.parse_csv(text)
    columns = list(rows[0].keys()) if rows else []

    saved_to = None
    if payload.save_csv and rows:
        output = payload.output_file or str(settings.events_output_abs)
        service.save_csv(rows, output)
        saved_to = output

    return SheetParseResponse(
        rows_count=len(rows),
        columns=columns,
        saved_to=saved_to,
        rows=rows,
    )
