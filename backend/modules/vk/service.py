import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from backend.app.config import settings


_MAX_RETRIES = 5
_RETRY_DELAY_SEC = 2
_INTER_REQUEST_DELAY_SEC = 0.34


class VKAPIError(RuntimeError):
    """Ошибка VK API или сети при работе с ним."""


# ---------- Публикация постов (бывший poster.py) ----------

def create_post(
    message: str,
    attachments: Optional[str] = None,
    from_group: bool = True,
) -> int:
    """
    Публикует пост на стену сообщества и возвращает ID поста.
    Бросает VKAPIError при ошибках сети / API.
    """

    params = {
        "owner_id": settings.OWNER_ID,
        "from_group": int(from_group),
        "message": message,
        "v": settings.VK_API_VERSION,
        "access_token": settings.ACCESS_TOKEN,
    }
    if attachments:
        params["attachments"] = attachments

    data = _post_with_retries(settings.VK_API_URL_POST, params)

    if "error" in data:
        raise VKAPIError(data["error"].get("error_msg", "VK API error"))

    return int(data["response"]["post_id"])


def post_url(post_id: int) -> str:
    return f"https://vk.com/wall{settings.OWNER_ID}_{post_id}"


# ---------- Парсинг стены (бывший parser.py) ----------

def fetch_posts(
    domain: Optional[str] = None,
    max_posts: Optional[int] = None,
) -> list[dict]:
    """Собирает посты со стены сообщества VK через wall.get."""

    domain = domain or settings.VK_PARSER_GROUP_DOMAIN
    max_posts = max_posts or settings.VK_PARSER_MAX_POSTS
    count = settings.VK_PARSER_COUNT_PER_REQUEST

    all_posts: list[dict] = []
    offset = 0

    while True:
        params = {
            "domain": domain,
            "count": count,
            "offset": offset,
            "v": settings.VK_API_VERSION,
            "access_token": settings.ACCESS_TOKEN,
        }
        data = _get_with_retries(settings.VK_API_URL_GET, params)

        if "error" in data:
            raise VKAPIError(data["error"].get("error_msg", "VK API error"))

        items = data["response"]["items"]
        total = data["response"]["count"]
        if not items:
            break

        all_posts.extend(items)
        offset += count

        if len(all_posts) >= max_posts:
            all_posts = all_posts[:max_posts]
            break
        if offset >= total:
            break
        time.sleep(_INTER_REQUEST_DELAY_SEC)

    return all_posts


def parse_post(post: dict) -> dict:
    """Извлекает интересующие поля из сырого VK-поста."""

    dt = datetime.fromtimestamp(post.get("date", 0))
    text = post.get("text", "").replace("\n", " ").replace(";", ",")
    return {
        "id": post.get("id"),
        "date": dt,
        "text": text,
        "likes": post.get("likes", {}).get("count", 0),
        "reposts": post.get("reposts", {}).get("count", 0),
        "comments": post.get("comments", {}).get("count", 0),
        "views": post.get("views", {}).get("count", 0),
    }


def save_posts_to_csv(posts: list[dict], filename: Optional[Path] = None) -> Path:
    """Сохраняет уже распарсенные посты в CSV. Возвращает путь к файлу."""

    path = Path(filename) if filename else settings.vk_parser_output_abs
    fieldnames = ["id", "date", "text", "likes", "reposts", "comments", "views"]

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for post in posts:
            row = dict(post)
            if isinstance(row.get("date"), datetime):
                row["date"] = row["date"].strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow(row)

    return path


# ---------- Внутренние HTTP-хелперы ----------

def _post_with_retries(url: str, params: dict) -> dict:
    last_err: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.post(url, data=params, timeout=15)
            return resp.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            last_err = e
            time.sleep(_RETRY_DELAY_SEC)
    raise VKAPIError(f"VK POST {url} не ответил после {_MAX_RETRIES} попыток: {last_err}")


def _get_with_retries(url: str, params: dict) -> dict:
    last_err: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=15)
            return resp.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            last_err = e
            time.sleep(_RETRY_DELAY_SEC)
    raise VKAPIError(f"VK GET {url} не ответил после {_MAX_RETRIES} попыток: {last_err}")
