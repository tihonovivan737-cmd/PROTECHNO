"""
Парсер публичной ленты канала на Дзен.

Берёт публикации канала через внутренний JSON API Дзена
(используется фронтендом dzen.ru) и сохраняет в CSV в стиле parser.py.

Лайки/комментарии в публичном ответе анониму не отдаются
(feedback_info пустой), поэтому в CSV пишутся только публично доступные
метрики: views, title, text-анонс, ссылка и время публикации (строкой,
как её отдаёт Дзен — например, "14 часов назад").
"""

import csv
import time
from urllib.parse import urlparse, parse_qs

import requests

CHANNEL_ID = "691017fdbee3845d70b9a02b"
OUTPUT_FILE = "dzen_posts.csv"
MAX_POSTS = 60  # сколько постов суммарно вытащить

API_FIRST = "https://dzen.ru/api/v3/launcher/more"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru,en;q=0.9",
    "Referer": f"https://dzen.ru/id/{CHANNEL_ID}",
}


def _get_json(session: requests.Session, url: str, params: dict | None = None) -> dict:
    """GET с ретраями и возвратом распарсенного JSON."""
    for attempt in range(5):
        try:
            resp = session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"  Ошибка сети (попытка {attempt + 1}/5): {e}")
            time.sleep(2)
    raise RuntimeError(f"Не удалось получить {url}")


def fetch_channel_posts(channel_id: str, max_posts: int = MAX_POSTS) -> tuple[list[dict], str]:
    """
    Тянет публикации канала постранично.
    Возвращает (items, channel_title).
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # Прогреваем сессию (получаем куки), иначе Дзен может редиректить на SSO.
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

        # Фильтруем только посты этого канала (на всякий случай).
        items = [i for i in items if i.get("publisher_id") == channel_id]

        if not channel_title and items:
            channel_title = items[0].get("domain_title", "") or ""

        all_items.extend(items)
        print(f"Загружено {len(all_items)} постов...")

        if len(all_items) >= max_posts:
            all_items = all_items[:max_posts]
            break

        more = data.get("more") or {}
        next_link = more.get("link")
        if not next_link:
            break

        # next_link — абсолютный URL с уже зашитыми query-параметрами
        # (channel_id, next_page_id, _csrf и т.д.).
        parsed = urlparse(next_link)
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        time.sleep(0.5)
        try:
            data = _get_json(session, base, params=params)
        except RuntimeError as e:
            print(f"  Пагинация прервана: {e}")
            break

    return all_items, channel_title


def parse_post(item: dict, channel_title: str = "") -> dict:
    """Извлекает интересующие поля из одного поста."""
    text = (item.get("text") or "").replace("\n", " ").replace(";", ",")
    title = (item.get("title") or "").replace("\n", " ").replace(";", ",")
    return {
        "id": item.get("publication_id") or item.get("id"),
        "date": item.get("creation_time", ""),  # Дзен отдаёт строкой ("14 часов назад")
        "title": title,
        "text": text,
        "views": item.get("views", 0) or 0,
        "time_to_read_sec": item.get("timeToReadSeconds", 0) or 0,
        "link": item.get("link", ""),
        "comments_link": item.get("comments_link", ""),
        "channel": channel_title,
    }


def save_to_csv(items: list[dict], filename: str, channel_title: str = "") -> None:
    if not items:
        print("Нет постов для сохранения.")
        return

    fieldnames = [
        "id",
        "date",
        "title",
        "text",
        "views",
        "time_to_read_sec",
        "link",
        "comments_link",
        "channel",
    ]
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for it in items:
            writer.writerow(parse_post(it, channel_title))

    print(f"Сохранено {len(items)} постов в {filename}")


def main() -> None:
    print(f"Парсинг канала Дзен: id={CHANNEL_ID}")
    items, channel_title = fetch_channel_posts(CHANNEL_ID, MAX_POSTS)
    if channel_title:
        print(f"Канал: {channel_title}")
    save_to_csv(items, OUTPUT_FILE, channel_title)


if __name__ == "__main__":
    main()
