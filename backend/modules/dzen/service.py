"""Парсер публичной ленты канала на Дзен.

Берёт публикации канала через внутренний JSON API Дзена
и возвращает структурированные данные. Может сохранять в CSV.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests

API_FIRST = "https://dzen.ru/api/v3/launcher/more"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru,en;q=0.9",
}


class DzenParserError(RuntimeError):
    """Ошибка парсинга Дзен."""


def _get_json(session: requests.Session, url: str, params: dict | None = None) -> dict:
    for attempt in range(5):
        try:
            resp = session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            if attempt == 4:
                raise DzenParserError(f"Не удалось получить {url}: {e}") from e
            time.sleep(2)
    raise DzenParserError(f"Не удалось получить {url}")


def fetch_channel_posts(channel_id: str, max_posts: int = 60) -> tuple[list[dict], str]:
    """Тянет публикации канала постранично. Возвращает (items, channel_title)."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Referer"] = f"https://dzen.ru/id/{channel_id}"

    try:
        session.get(f"https://dzen.ru/id/{channel_id}?is_autologin_ya=true", timeout=15)
    except requests.exceptions.RequestException:
        pass

    all_items: list[dict] = []
    channel_title = ""

    data = _get_json(session, API_FIRST, params={"channel_id": channel_id})

    while True:
        items = data.get("items", []) or []
        if not items:
            break

        items = [i for i in items if i.get("publisher_id") == channel_id]

        if not channel_title and items:
            channel_title = items[0].get("domain_title", "") or ""

        all_items.extend(items)

        if len(all_items) >= max_posts:
            all_items = all_items[:max_posts]
            break

        more = data.get("more") or {}
        next_link = more.get("link")
        if not next_link:
            break

        parsed = urlparse(next_link)
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        time.sleep(0.5)
        try:
            data = _get_json(session, base, params=params)
        except DzenParserError:
            break

    return all_items, channel_title


def parse_post(item: dict, channel_title: str = "") -> dict:
    """Извлекает интересующие поля из одного поста."""
    text = (item.get("text") or "").replace("\n", " ").replace(";", ",")
    title = (item.get("title") or "").replace("\n", " ").replace(";", ",")
    return {
        "id": item.get("publication_id") or item.get("id"),
        "date": item.get("creation_time", ""),
        "title": title,
        "text": text,
        "views": item.get("views", 0) or 0,
        "time_to_read_sec": item.get("timeToReadSeconds", 0) or 0,
        "link": item.get("link", ""),
        "comments_link": item.get("comments_link", ""),
        "channel": channel_title,
    }


def save_to_csv(items: list[dict], filename: str | Path, channel_title: str = "") -> int:
    """Сохраняет посты в CSV. Возвращает количество сохранённых."""
    if not items:
        return 0

    fieldnames = [
        "id", "date", "title", "text", "views",
        "time_to_read_sec", "link", "comments_link", "channel",
    ]
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for it in items:
            writer.writerow(parse_post(it, channel_title))

    return len(items)
