from abc import ABC, abstractmethod, abstractclassmethod
import requests
import re

class BaseLLMClient(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

class BasePromptBuilder(ABC):

    @abstractmethod
    def build_prompt(self, query: str) -> str:
        raise NotImplementedError

class BaseExampleStore(ABC):

    @abstractclassmetod
    def _load(cls, path: Path) -> list[dict]:
        raise NotImplementedError

    @abstractclassmethod
    def _clean_text(cls, text: str) -> str:
        raise NotImplementedError

    def top_by_likes(self, n: int, min_len: int = 0, max_len: int = 10_000) -> list[dict]:
        raise NotImplementedError

class CSVExampleStore:

    _VK_LINK_RE = re.compile(r"\[(?:[^\]|]+)\|([^\]]+)\]")
    _MULTISPACE_RE = re.compile(r"[ \t]+")

    def __init__(self, path: Path):
        self.rows = self._load(path)

    @classmethod
    def _load(cls, path: Path) -> list[dict]:
        if not path.exists():
            raise FileNotFoundError(f"CSV не найден: {path}")
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            rows = []
            for r in reader:
                text = cls._clean_text(r.get("text", ""))
                if not text:
                    continue
                rows.append({
                    "id": r.get("id", ""),
                    "date": r.get("date", ""),
                    "text": text,
                    "likes": cls._to_int(r.get("likes")),
                    "views": cls._to_int(r.get("views")),
                })
            return rows

    @classmethod
    def _clean_text(cls, text: str) -> str:
        text = cls._VK_LINK_RE.sub(r"\1", text)      
        text = text.replace("\u00a0", " ")             
        text = cls._MULTISPACE_RE.sub(" ", text)
        return text.strip()

    @staticmethod
    def _to_int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def top_by_likes(self, n: int, min_len: int = 0, max_len: int = 10_000) -> list[dict]:
        filtered = [r for r in self.rows if min_len <= len(r["text"]) <= max_len]
        return sorted(filtered, key=lambda r: r["likes"], reverse=True)[:n]

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