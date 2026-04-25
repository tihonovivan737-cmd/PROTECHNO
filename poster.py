import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

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


def upload_photo_by_url(photo_url: str, group_id: int, token: str) -> str | None:
    """Скачивает фото по URL, загружает на стену VK и возвращает attachment-строку."""
    try:
        img_resp = requests.get(photo_url, timeout=30)
        img_resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка скачивания фото: {e}")
        return None

    upload_server_url = "https://api.vk.com/method/photos.getWallUploadServer"
    params = {
        "group_id": group_id,
        "v": API_VERSION,
        "access_token": token,
    }
    try:
        resp = requests.get(upload_server_url, params=params, timeout=15)
        data = resp.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Ошибка получения upload_url: {e}")
        return None

    if "error" in data:
        print(f"Ошибка VK API (getWallUploadServer): {data['error']['error_msg']}")
        return None

    upload_url = data["response"]["upload_url"]

    try:
        files = {"photo": ("photo.jpg", img_resp.content)}
        upload_resp = requests.post(upload_url, files=files, timeout=30)
        upload_data = upload_resp.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Ошибка загрузки фото на сервер VK: {e}")
        return None

    if "error" in upload_data:
        print(f"Ошибка загрузки: {upload_data['error']}")
        return None

    save_url = "https://api.vk.com/method/photos.saveWallPhoto"
    save_params = {
        "group_id": group_id,
        "photo": upload_data["photo"],
        "server": upload_data["server"],
        "hash": upload_data["hash"],
        "v": API_VERSION,
        "access_token": token,
    }
    try:
        save_resp = requests.get(save_url, params=save_params, timeout=15)
        save_data = save_resp.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Ошибка сохранения фото: {e}")
        return None

    if "error" in save_data:
        print(f"Ошибка VK API (saveWallPhoto): {save_data['error']['error_msg']}")
        return None

    photo = save_data["response"][0]
    return f"photo{photo['owner_id']}_{photo['id']}"


def create_post(message: str, attachments: str | list[str] | None = None, from_group: bool = True) -> int | None:
    """
    Публикует пост на стену сообщества.

    :param message: Текст поста
    :param attachments: Вложения VK (например "photo123_456") или URL фото.
                        Можно передать несколько через запятую или список.
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
        if isinstance(attachments, str):
            items = [item.strip() for item in attachments.split(",") if item.strip()]
        else:
            items = [str(item).strip() for item in attachments if str(item).strip()]

        processed = []
        for item in items:
            if item.startswith("http"):
                att = upload_photo_by_url(item, group_id, token)
                if att:
                    processed.append(att)
                else:
                    print(f"Не удалось загрузить фото: {item}")
            else:
                processed.append(item)

        if processed:
            params["attachments"] = ",".join(processed)
        else:
            print("Не удалось подготовить вложения — публикация отменена.")
            return None

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
    attachments = input("Вложения (URL или photo123_456, несколько через запятую; Enter если нет): ").strip() or None
    create_post(message, attachments=attachments)


if __name__ == "__main__":
    main()