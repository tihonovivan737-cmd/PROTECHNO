import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Грузим .env, лежащий рядом с этим файлом — независимо от cwd.
# override=True — значения из .env побеждают пустые/устаревшие переменные окружения.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

API_VERSION = "5.199"

def _vk_config() -> tuple[str, str, int]:
    """Достаёт настройки VK из окружения. Падает осмысленно, если чего-то нет."""

    token = os.getenv("ACCESS_TOKEN")
    api_url = os.getenv("VK_API_URL_POST")
    group_id = os.getenv("GROUP_ID")
    if not token or not api_url or not group_id:
        raise RuntimeError(
            "Не заданы переменные окружения: ACCESS_TOKEN / VK_API_URL_POST / GROUP_ID"
        )
    return token, api_url, int(group_id)


def create_post(message: str, attachments: str | None = None, from_group: bool = True) -> int | None:
    """
    Публикует пост на стену сообщества.

    :param message: Текст поста
    :param attachments: Вложения VK, например "photo123_456"
    :param from_group: True — пост от имени сообщества
    :return: ID опубликованного поста или None при ошибке
    """

    token, api_url, group_id = _vk_config()

    params = {
        "owner_id": -group_id,
        "from_group": int(from_group),
        "message": message,
        "v": API_VERSION,
        "access_token": token,
    }
    if attachments:
        params["attachments"] = attachments

    data = None
    for attempt in range(5):
        try:
            resp = requests.post(api_url, data=params, timeout=15)
            data = resp.json()
            break
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"  Ошибка сети (попытка {attempt + 1}/5): {e}")
            time.sleep(2)
    else:
        print("Не удалось выполнить запрос после 5 попыток.")
        return None

    if "error" in data:
        print(f"Ошибка VK API: {data['error']['error_msg']}")
        return None

    post_id = data["response"]["post_id"]
    print(f"Пост опубликован! ID: {post_id}")
    print(f"Ссылка: https://vk.com/wall-{group_id}_{post_id}")
    return post_id


def main():
    message = input("Введите текст поста: ").strip()
    if not message:
        print("Текст поста не может быть пустым.")
        return
    attachments = input("Вложения (оставьте пустым, если нет): ").strip() or None
    create_post(message, attachments=attachments)


if __name__ == "__main__":
    main()