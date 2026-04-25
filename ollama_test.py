from abc import ABC, abstractmethod
import requests

class BaseLLMClient(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

class PromptBuilder:

    EXAMPLE_INPUT = "Открытие пространства Молодёжного центра «Своё дело» на Попова, 12"

    EXAMPLE_OUTPUT = (
        "Мы находимся на Попова, 12, чтобы каждый смог найти дело по душе — "
        "развил свои навыки в медиасфере, научился танцевать, разработал новый "
        "тренинг или проект, стал частью большой команды интеллектуальных или "
        "настольных игр, вышел на поле в Летней или Зимней дворовой футбольной "
        "лиге, вступил в Ассоциацию работающей молодежи, прошел первый инструктаж "
        "в Трудовом отряде Главы города Красноярска и получил первый опыт "
        "официальной работы, и просто делал то, что любит…\n\n"
        "Смотри на наши помещения во вкладке «Товары», выбирай любое из них для "
        "бронирования и заполняй инициативную заявку — это бесплатно!\n\n"
        "Главное, что все дороги ведут в #мцсвоедело!"
    )

    SYSTEM = (
        "Ты — SMM-редактор молодёжного медиасообщества «Своё дело» (Красноярск).\n"
        "Твоя задача: из краткого описания события сделать готовый пост для соцсетей.\n"
        "\n"
        "СТИЛЬ:\n"
        "- Дружелюбный, тёплый, вдохновляющий, без канцелярита и пафоса.\n"
        "- Обращение на «ты», как к ровеснику.\n"
        "- Живые перечисления через тире, длинные предложения допустимы.\n"
        "- Уместные эмодзи (1–4 на пост), без перебора.\n"
        "- Тон — как в эталонном примере ниже.\n"
        "\n"
        "СТРУКТУРА:\n"
        "1) Цепляющий первый абзац — суть и атмосфера события.\n"
        "2) Конкретика: что будет / что можно сделать / для кого.\n"
        "3) Призыв к действию (как поучаствовать, куда писать, что нажать).\n"
        "4) Финальная строка с хэштегом #мцсвоедело и, при уместности, "
        "1–2 дополнительными хэштегами.\n"
        "\n"
        "ПРАВИЛА:\n"
        "- НЕ выдумывай факты, даты, имена, адреса, цены, которых нет в описании.\n"
        "- Если данных мало — пиши обобщённо, без конкретики.\n"
        "- Длина: 80–180 слов.\n"
        "- Никаких пояснений, мета-комментариев и markdown — только текст поста.\n"
    )

    FEWSHOT_USER = f"Описание события:\n{EXAMPLE_INPUT}"
    FEWSHOT_ASSISTANT = EXAMPLE_OUTPUT

    def build_prompt(self, query: str) -> str:
        return f"Описание события:\n{query.strip()}"


class OllamaClient(BaseLLMClient):
    def __init__(self, url: str, model: str, timeout: int = 120):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, system: str, user: str) -> str:
        try:
            response = requests.post(
                f"{self.url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": PromptBuilder.FEWSHOT_USER},
                        {"role": "assistant", "content": PromptBuilder.FEWSHOT_ASSISTANT},
                        {"role": "user", "content": user},
                    ],
                    "options": {
                        "temperature": 0.8,   
                        "top_p": 0.9,
                        "top_k": 40,
                        "repeat_penalty": 1.1,
                        "num_predict": 600,
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except Exception as e:
            return f"LLM error: {e}"


OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:3b"
QUERY = "Событие Росмолодёжи на острове Татышев"

def main():
    client = OllamaClient(url=OLLAMA_URL, model=MODEL)
    builder = PromptBuilder()

    print(f"Ollama: {OLLAMA_URL} | model: {MODEL}")
    print(f"query> {QUERY}\n")

    answer = client.generate(
        system=builder.SYSTEM,
        user=builder.build_prompt(QUERY),
    )
    print(f"bot> {answer}\n")


if __name__ == "__main__":
    main()