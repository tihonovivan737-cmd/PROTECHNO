from typing import Optional

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    platform: str = Field(
        ...,
        description="Площадка: 'vk' или 'dzen'",
    )
    csv_path: Optional[str] = Field(
        default=None,
        description="Путь к CSV с данными. По умолчанию — стандартный файл площадки",
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Путь для сохранения PDF. По умолчанию — report_{platform}.pdf",
    )


class ReportGenerateResponse(BaseModel):
    platform: str
    output_path: str
    message: str = "Отчёт успешно сгенерирован"
