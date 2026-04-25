import os
import requests
import csv
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

GROUP_DOMAIN = "svoedelomc"
OUTPUT_FILE = "posts.csv"

API_VERSION = "5.199"
API_URL_GET = os.getenv("VK_API_URL_GET")
COUNT_PER_REQUEST = 10
MAX_POSTS = 10


def fetch_members_count(domain, token):
    """Получает количество подписчиков сообщества."""
    url = "https://api.vk.com/method/groups.getById"
    params = {
        "group_id": domain,
        "fields": "members_count",
        "v": API_VERSION,
        "access_token": token,
    }
    for attempt in range(5):
        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            if "error" in data:
                print(f"Ошибка VK API (groups.getById): {data['error']['error_msg']}")
                return 0
            group = data["response"]["groups"][0]
            return group.get("members_count", 0)
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"  Ошибка сети при получении подписчиков (попытка {attempt + 1}/5): {e}")
            time.sleep(2)
    print("Не удалось получить количество подписчиков.")
    return 0


def fetch_posts(domain, token):
    """Получает все посты со стены паблика через VK API."""

    all_posts = []
    offset = 0

    while True:
        params = {
            "domain": domain,
            "count": COUNT_PER_REQUEST,
            "offset": offset,
            "v": API_VERSION,
            "access_token": token,
        }

        for attempt in range(5):
            try:
                resp = requests.get(API_URL_GET, params=params, timeout=15)
                data = resp.json()
                break
            except (requests.exceptions.RequestException, ValueError) as e:
                print(f"  Ошибка сети (попытка {attempt + 1}/5): {e}")
                time.sleep(2)
        else:
            print("Не удалось выполнить запрос после 5 попыток, сохраняю то что есть...")
            break

        if "error" in data:
            print(f"Ошибка VK API: {data['error']['error_msg']}")
            break

        items = data["response"]["items"]
        total = data["response"]["count"]

        if not items:
            break

        all_posts.extend(items)
        offset += COUNT_PER_REQUEST

        print(f"Загружено {len(all_posts)} / {total} постов...")

        if len(all_posts) >= MAX_POSTS:
            all_posts = all_posts[:MAX_POSTS]
            break

        if offset >= total:
            break
        time.sleep(0.34)

    return all_posts

def parse_post(post, members_count=0):
    """Извлекает нужные поля из поста."""

    dt = datetime.fromtimestamp(post.get("date", 0)).strftime("%Y-%m-%d %H:%M:%S")
    text = post.get("text", "").replace("\n", " ").replace(";", ",")
    return {
        "id": post.get("id"),
        "date": dt,
        "text": text,
        "likes": post.get("likes", {}).get("count", 0),
        "reposts": post.get("reposts", {}).get("count", 0),
        "comments": post.get("comments", {}).get("count", 0),
        "views": post.get("views", {}).get("count", 0),
        "group_members": members_count,
    }


def save_to_csv(posts, filename, members_count=0):
    """Сохраняет посты в CSV-файл."""

    if not posts:
        print("Нет постов для сохранения.")
        return

    fieldnames = ["id", "date", "text", "likes", "reposts", "comments", "views", "group_members"]

    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for post in posts:
            writer.writerow(parse_post(post, members_count))

    print(f"Сохранено {len(posts)} постов в {filename}")


def main():
    print(f"Парсинг постов из vk.com/{GROUP_DOMAIN}...")
    posts = fetch_posts(GROUP_DOMAIN, ACCESS_TOKEN)
    time.sleep(0.34)
    members_count = fetch_members_count(GROUP_DOMAIN, ACCESS_TOKEN)
    print(f"Подписчиков в сообществе: {members_count}")
    save_to_csv(posts, OUTPUT_FILE, members_count)


if __name__ == "__main__":
    main()