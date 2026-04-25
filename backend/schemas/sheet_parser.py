from typing import Optional

from pydantic import BaseModel, Field


class SheetParseRequest(BaseModel):
    sheet_id: Optional[str] = Field(
        default=None,
        description="ID Google-таблицы. По умолчанию — из .env (GOOGLE_SHEET_ID)",
    )
    gid: Optional[str] = Field(
        default=None,
        description="GID листа. По умолчанию — из .env (GOOGLE_SHEET_GID)",
    )
    save_csv: bool = Field(default=False, description="Сохранить результат в CSV")
    output_file: Optional[str] = Field(
        default=None,
        description="Имя CSV-файла (если save_csv=true). По умолчанию — events.csv",
    )


class SheetParseResponse(BaseModel):
    rows_count: int
    columns: list[str]
    saved_to: Optional[str] = None
    rows: list[dict]
