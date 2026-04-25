"""Парсер публичной Google-таблицы (доступ по ссылке) без service account.

Скачивает лист как CSV через export-эндпоинт Google Sheets.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import requests

EXPORT_URL = "https://docs.google.com/spreadsheets/d/{sheet_id}/export"


class SheetParserError(RuntimeError):
    """Ошибка парсинга Google Sheets."""


def fetch_sheet_csv(sheet_id: str, gid: str = "0") -> str:
    """Качает лист Google Sheets как CSV-текст."""
    try:
        resp = requests.get(
            EXPORT_URL.format(sheet_id=sheet_id),
            params={"format": "csv", "gid": gid},
            timeout=30,
            allow_redirects=True,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except requests.exceptions.RequestException as e:
        raise SheetParserError(f"Не удалось скачать таблицу: {e}") from e


def parse_csv(text: str) -> list[dict]:
    """Парсит CSV-текст в список словарей по заголовкам первой строки."""
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def save_csv(rows: list[dict], filename: str | Path) -> int:
    """Сохраняет строки в CSV (разделитель ';', UTF-8 с BOM). Возвращает кол-во строк."""
    if not rows:
        return 0

    fieldnames = list(rows[0].keys())
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)
