from ollama_test import generate_post_text
from poster import create_post


def main() -> None:
    query = input("Опиши событие одной фразой: ").strip()
    if not query:
        print("Пустое описание — выходим.")
        return

    print("\nГенерирую текст поста через LLM...\n")
    text = generate_post_text(query)

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

    attachments = input("Вложения (опц., например photo123_456): ").strip() or None
    create_post(text, attachments=attachments)


if __name__ == "__main__":
    main()