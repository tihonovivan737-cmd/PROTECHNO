import csv
import os
from pathlib import Path

from condition import assess as assess_condition
from ollama_test import DEFAULT_PROFILE, PROFILES, generate_post_text
from poster import create_post


def choose_profile() -> str:
    """Спрашивает у пользователя профиль площадки. Возвращает имя профиля."""
    profiles = list(PROFILES.items())
    print("\nВыбери профиль площадки:")
    for idx, (name, mod) in enumerate(profiles, start=1):
        marker = " (по умолчанию)" if name == DEFAULT_PROFILE else ""
        print(f"  {idx}. {mod.TITLE} [{name}]{marker}")

    raw = input(f"Номер профиля [Enter = {DEFAULT_PROFILE}]: ").strip()
    if not raw:
        return DEFAULT_PROFILE
    if raw.isdigit():
        i = int(raw)
        if 1 <= i <= len(profiles):
            return profiles[i - 1][0]
    if raw in PROFILES:
        return raw
    print(f"Не понял выбор — использую профиль по умолчанию: {DEFAULT_PROFILE}.")
    return DEFAULT_PROFILE
def load_events(path: Path) -> list[dict]:
    """Загружает events.csv с разделителем ';'."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        return [row for row in reader]


def pick_event_by_date(events: list[dict], date_str: str) -> dict | None:
    """Ищет событие по дате (формат dd.mm.yyyy)."""
    date_str = date_str.strip()
    for ev in events:
        if ev.get("Дата проведения", "").strip() == date_str:
            return ev
    return None


def main() -> None:
    profile = choose_profile()
    print(f"Профиль: {PROFILES[profile].TITLE} [{profile}]\n")

    print("1 — Выбрать событие из таблицы по дате")
    print("2 — Ввести описание вручную")
    choice = input("Ваш выбор [1/2]: ").strip()
    query = ""

    if choice == "1":
        events_file = Path(os.getenv("EVENTS_OUTPUT_FILE", "events.csv"))
        events = load_events(events_file)
        if not events:
            print(f"Файл {events_file} не найден или пуст.")
            return

        print("\nДоступные события:")
        for idx, ev in enumerate(events, start=1):
            print(f"  {idx}. {ev.get('Дата проведения', '???')} — {ev.get('Название мероприятия', '???')}")

        date_input = input("\nВведите дату события (дд.мм.гггг): ").strip()
        event = pick_event_by_date(events, date_input)
        if not event:
            print("Событие с такой датой не найдено.")
            return

        query = event.get("Название мероприятия", "").strip()
        draft = input("Добавь сырой набросок поста (будет склеено с событием), или Enter: ").strip()
        if draft:
            query = f"{query}\n\n{draft}"
        print(f"\nИтоговый запрос:\n{query}\n")
    elif choice == "2":
        query = input("Введи сырой набросок поста: ").strip()
    else:
        print("Неверный выбор.")
        return

    if not query:
        print("Пустое описание — выходим.")
        return

    condition = assess_condition()
    print(
        f"\nСостояние сообщества: {condition.state} "
        f"(avg_er={condition.avg_er:.4f}, "
        f"crisis<{condition.crisis_threshold:.4f}, "
        f"rise>{condition.rise_threshold:.4f}, "
        f"по {condition.sample_size} последним постам)"
    )

    print("\nГенерирую текст поста через LLM...\n")
    text = generate_post_text(query, state=condition.state, profile=profile)
    print("=" * 60)
    print(text)
    print("=" * 60)
    if not text or text.startswith("LLM error:"):
        print("Текст не получен — публикация отменена.")
        return

    confirm = input("\nОпубликовать в VK? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Отменено.")
        return

    attachments = input("Вложения (опц., например photo123_456 или URL, несколько через запятую): ").strip() or None
    try:
        create_post(text, attachments=attachments)
    except RuntimeError as e:
        print(f"Ошибка публикации: {e}")
        print("Убедитесь, что в .env заданы ACCESS_TOKEN, GROUP_ID и VK_API_URL_POST.")


if __name__ == "__main__":
    main()