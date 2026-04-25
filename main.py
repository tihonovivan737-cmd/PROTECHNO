from backend.modules.llm.service import generate_post_text, LLMError
from backend.modules.vk.service import VKAPIError, create_post, post_url


def main() -> None:
    query = input("Опиши событие одной фразой: ").strip()
    if not query:
        print("Пустое описание — выходим.")
        return

    print("\nГенерирую текст поста через LLM...\n")
    try:
        text, model, shots = generate_post_text(query)
    except LLMError as e:
        print(f"LLM error: {e}")
        return

    print("=" * 60)
    print(text)
    print("=" * 60)
    print(f"(model={model}, shots={shots})")

    if not text:
        print("Текст не получен — публикация отменена.")
        return

    confirm = input("\nОпубликовать в VK? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Отменено.")
        return

    attachments = input("Вложения (опц., например photo123_456): ").strip() or None
    try:
        post_id = create_post(text, attachments=attachments)
    except VKAPIError as e:
        print(f"Ошибка публикации: {e}")
        return

    print(f"Пост опубликован! ID: {post_id}")
    print(f"Ссылка: {post_url(post_id)}")


if __name__ == "__main__":
    main()