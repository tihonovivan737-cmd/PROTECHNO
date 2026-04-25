"""Парсер публичной Google-таблицы (доступ по ссылке) без service account.

Скачивает лист как CSV через export-эндпоинт Google Sheets и сохраняет локально.
Идентификатор таблицы и gid берутся из .env.
"""

import csv
import io
import os

import requests
from dotenv import load_dotenv

load_dotenv()

EXPORT_URL = "https://docs.google.com/spreadsheets/d/{sheet_id}/export"


def fetch_sheet_csv(sheet_id: str, gid: str = "0") -> str:
    """Качает лист Google Sheets как CSV-текст."""
    params = {"format": "csv", "gid": gid}
    resp = requests.get(
        EXPORT_URL.format(sheet_id=sheet_id),
        params=params,
        timeout=30,
        allow_redirects=True,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def parse_csv(text: str) -> list[dict]:
    """Парсит CSV-текст в список словарей по заголовкам первой строки."""
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def save_csv(rows: list[dict], filename: str) -> None:
    """Сохраняет строки в CSV (разделитель ';', UTF-8 с BOM для Excel)."""
    if not rows:
        print("Нет данных для сохранения.")
        return

    fieldnames = list(rows[0].keys())
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Сохранено {len(rows)} строк в {filename}")


def main() -> None:
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise SystemExit("Не задан GOOGLE_SHEET_ID в .env")

    gid = os.getenv("GOOGLE_SHEET_GID", "0")
    output = os.getenv("EVENTS_OUTPUT_FILE", "events.csv")

    print(f"Скачиваю таблицу {sheet_id} (gid={gid})...")
    text = fetch_sheet_csv(sheet_id, gid)
    rows = parse_csv(text)
    print(f"Прочитано строк: {len(rows)}")

    save_csv(rows, output)


if __name__ == "__main__":
    main()
