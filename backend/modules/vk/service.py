import csv
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from backend.app.config import settings


_MAX_RETRIES = 5
_RETRY_DELAY_SEC = 2
_INTER_REQUEST_DELAY_SEC = 0.34

# Разрешённые символы в коротком имени VK-сообщества.
_VK_DOMAIN_RE = re.compile(r"^[A-Za-z0-9_.]{1,64}$")
# Разбор ссылки вида https://vk.com/<path>.
_VK_URL_RE = re.compile(
    r"^(?:https?://)?(?:m\.|www\.)?vk\.com/(?P<path>[A-Za-z0-9_.]+)/?$",
    re.IGNORECASE,
)
# Числовые идентификаторы сообщества: club123 / public123.
_NUMERIC_ID_RE = re.compile(r"^(?:club|public)(?P<id>\d+)$", re.IGNORECASE)
# Зарезервированные пути на vk.com, которые не являются сообществами.
_RESERVED_PATHS = {
    "feed", "im", "id0", "settings", "friends", "groups", "photos",
    "video", "audio", "messages", "search", "login", "support",
}
# Коды ошибок VK API, которые означают «ссылка ведёт не туда»
# (несуществующее / удалённое / приватное сообщество).
# Док: https://dev.vk.com/reference/errors
_VK_INVALID_TARGET_ERROR_CODES = {
    15,   # Access denied
    100,  # One of the parameters specified was missing or invalid
    104,  # Not found
    125,  # Invalid group id
    203,  # Access to group denied
}


class VKAPIError(RuntimeError):
    """Ошибка VK API или сети при работе с ним."""


class InvalidVKUrlError(ValueError):
    """Невалидная ссылка/идентификатор VK-сообщества."""


def parse_vk_community_ref(url_or_domain: str) -> dict:
    """
    Превращает ссылку/идентификатор сообщества VK в параметры для wall.get.

    Поддерживается:
      - 'svoedelomc'                 -> {'domain': 'svoedelomc'}
      - 'vk.com/svoedelomc'          -> {'domain': 'svoedelomc'}
      - 'https://vk.com/svoedelomc'  -> {'domain': 'svoedelomc'}
      - 'https://vk.com/club123'     -> {'owner_id': -123}
      - 'https://vk.com/public123'   -> {'owner_id': -123}

    Бросает InvalidVKUrlError для пустых строк, чужих доменов,
    личных профилей (id123) и зарезервированных путей.
    """

    if url_or_domain is None:
        raise InvalidVKUrlError("Ссылка на сообщество VK не передана")

    raw = url_or_domain.strip()
    if not raw:
        raise InvalidVKUrlError("Ссылка на сообщество VK не может быть пустой")

    # Если похоже на URL — он обязан быть с домена vk.com.
    looks_like_url = "://" in raw or "/" in raw or raw.lower().startswith("vk.com")
    if looks_like_url:
        match = _VK_URL_RE.match(raw)
        if not match:
            raise InvalidVKUrlError(
                "Ожидается ссылка вида https://vk.com/<сообщество>"
            )
        path = match.group("path")
    else:
        path = raw

    path_lower = path.lower()

    if path_lower in _RESERVED_PATHS:
        raise InvalidVKUrlError(
            f"'{path}' — служебная страница VK, а не сообщество"
        )

    # Личные профили вида id123 не поддерживаем — это не группа.
    if re.fullmatch(r"id\d+", path_lower):
        raise InvalidVKUrlError(
            "Это ссылка на личный профиль, а не на сообщество"
        )

    numeric = _NUMERIC_ID_RE.match(path)
    if numeric:
        return {"owner_id": -int(numeric.group("id")), "domain_label": path}

    if not _VK_DOMAIN_RE.match(path):
        raise InvalidVKUrlError(
            "Короткое имя сообщества может содержать только латиницу, цифры, '_' и '.'"
        )

    return {"domain": path, "domain_label": path}

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
    url: str,
    max_posts: Optional[int] = None,
) -> tuple[list[dict], str]:
    """
    Собирает посты со стены сообщества VK по ссылке/идентификатору.
    Возвращает (raw_posts, domain_label).

    Бросает InvalidVKUrlError, если ссылка не валидна или сообщество
    не найдено / закрыто. VKAPIError — для остальных ошибок VK / сети.
    """

    ref = parse_vk_community_ref(url)
    domain_label = ref.pop("domain_label")
    max_posts = max_posts or settings.VK_PARSER_MAX_POSTS
    count = settings.VK_PARSER_COUNT_PER_REQUEST

    all_posts: list[dict] = []
    offset = 0

    while True:
        params = {
            **ref,
            "count": count,
            "offset": offset,
            "v": settings.VK_API_VERSION,
            "access_token": settings.ACCESS_TOKEN,
        }
        data = _get_with_retries(settings.VK_API_URL_GET, params)

        if "error" in data:
            err = data["error"]
            code = err.get("error_code")
            msg = err.get("error_msg", "VK API error")
            if code in _VK_INVALID_TARGET_ERROR_CODES:
                raise InvalidVKUrlError(
                    f"Сообщество '{domain_label}' недоступно: {msg}"
                )
            raise VKAPIError(msg)

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

    return all_posts, domain_label

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
