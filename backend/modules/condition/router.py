from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from backend.app.config import settings
from backend.modules.condition import service
from backend.schemas.condition import AssessRequest, AssessResponse

router = APIRouter(prefix="/api/condition", tags=["condition"])


@router.post("/assess", response_model=AssessResponse)
def assess_condition(payload: AssessRequest) -> AssessResponse:
    csv_path = Path(payload.csv_path) if payload.csv_path else settings.vk_parser_output_abs

    if not csv_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV не найден: {csv_path}",
        )

    result = service.assess(path=csv_path, window=payload.window)
    return AssessResponse(
        state=result.state,
        avg_er=result.avg_er,
        crisis_threshold=result.crisis_threshold,
        rise_threshold=result.rise_threshold,
        sample_size=result.sample_size,
    )
