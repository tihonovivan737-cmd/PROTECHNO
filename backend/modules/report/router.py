from fastapi import APIRouter, HTTPException, status

from backend.modules.report import service
from backend.schemas.report import ReportGenerateRequest, ReportGenerateResponse

router = APIRouter(prefix="/api/report", tags=["report"])


@router.post("/generate", response_model=ReportGenerateResponse)
def generate_report(payload: ReportGenerateRequest) -> ReportGenerateResponse:
    try:
        output = service.generate_report(
            platform=payload.platform,
            csv_path=payload.csv_path,
            output_path=payload.output_path,
        )
    except service.ReportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка генерации отчёта: {e}",
        )

    return ReportGenerateResponse(
        platform=payload.platform,
        output_path=output,
    )
