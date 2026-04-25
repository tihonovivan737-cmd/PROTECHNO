import requests
import csv
import time
from datetime import datetime

ACCESS_TOKEN = "vk1.a.QhPc8KVE4BUXd7vGk5YCOY240aLsuJEK7HADb6OyOBiUbhvP8bN6RIMkdTGiLOC4x1l17HyZJVO_zJm8yC7YgChAe92wRGqjGrxyBt1ZMUatdJej2Nu_3LOoCbUlnhcip2tyi3A6eQbPa-wViKWbVy81fzLpJtoMGct7suNQc-jO4b_lBhVNJuhzK6iMQS2CfHoumAAhUjxLQoiXZzKU1Q"

GROUP_DOMAIN = "svoedelomc"
OUTPUT_FILE = "posts.csv"

API_VERSION = "5.199"
API_URL = "https://api.vk.com/method/wall.get"
COUNT_PER_REQUEST = 10
MAX_POSTS = 10


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
                resp = requests.get(API_URL, params=params, timeout=15)
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

def parse_post(post):
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
    }


def save_to_csv(posts, filename):
    """Сохраняет посты в CSV-файл."""
    if not posts:
        print("Нет постов для сохранения.")
        return

    fieldnames = ["id", "date", "text", "likes", "reposts", "comments", "views"]

    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for post in posts:
            writer.writerow(parse_post(post))

    print(f"Сохранено {len(posts)} постов в {filename}")


def main():
    print(f"Парсинг постов из vk.com/{GROUP_DOMAIN}...")
    posts = fetch_posts(GROUP_DOMAIN, ACCESS_TOKEN)
    save_to_csv(posts, OUTPUT_FILE)


if __name__ == "__main__":
    main()