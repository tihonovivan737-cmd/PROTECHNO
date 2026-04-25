from abc import ABC, abstractmethod
import requests
import re
from pathlib import Path
from typing import Iterable
import csv

class BaseLLMClient(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

class BasePromptBuilder(ABC):

    @abstractmethod
    def build_prompt(self, query: str) -> str:
        raise NotImplementedError

class BaseExampleStore(ABC):

    @abstractmethod
    def top_by_likes(self, n: int, min_len: int = 0, max_len: int = 10_000) -> list[dict]:
        raise NotImplementedError

class CSVExampleStore(BaseExampleStore):

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

class PromptBuilder(BasePromptBuilder):
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
        "Из краткого описания события делаешь готовый пост для соцсетей.\n\n"
        "СТИЛЬ:\n"
        "- Дружелюбный, тёплый, вдохновляющий, без канцелярита и пафоса.\n"
        "- Обращение на «ты», как к ровеснику.\n"
        "- Живые перечисления через тире, длинные предложения допустимы.\n"
        "- Уместные эмодзи (1–4 на пост), без перебора.\n"
        "- Тон — как в примерах ниже.\n\n"
        "СТРУКТУРА:\n"
        "1) Цепляющий первый абзац — суть и атмосфера события.\n"
        "2) Конкретика: что будет / что можно сделать / для кого.\n"
        "3) Призыв к действию (как поучаствовать, куда писать, что нажать).\n"
        "4) Финальная строка с хэштегом #мцсвоедело и 1–2 доп. хэштегами.\n\n"
        "ПРАВИЛА:\n"
        "- Примеры задают СТИЛЬ. Факты бери ТОЛЬКО из текущего описания.\n"
        "- НЕ выдумывай факты, даты, имена, адреса, цены.\n"
        "- Если данных мало — пиши обобщённо, без конкретики.\n"
        "- Длина: 80–180 слов.\n"
        "- Никаких пояснений и markdown — только текст поста."
    )

    @staticmethod
    def _brief_from_post(post_text: str, max_len: int = 120) -> str:
        first = re.split(r"(?<=[.!?…])\s", post_text, maxsplit=1)[0]
        return (first[:max_len] + "…") if len(first) > max_len else first

    def build_prompt(self, query: str, shots: Iterable[dict] = ()) -> list[dict]:
        messages = [{"role": "system", "content": self.SYSTEM}]

        messages.append({"role": "user", "content": f"Описание события:\n{self.EXAMPLE_INPUT}"})
        messages.append({"role": "assistant", "content": self.EXAMPLE_OUTPUT})

        for shot in shots:
            brief = self._brief_from_post(shot["text"])
            messages.append({"role": "user", "content": f"Описание события:\n{brief}"})
            messages.append({"role": "assistant", "content": shot["text"]})

        messages.append({"role": "user", "content": f"Описание события:\n{query.strip()}"})
        return messages


class OllamaClient(BaseLLMClient):
    def __init__(self, url: str, model: str, timeout: int = 120):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, messages: list[dict]) -> str:
        try:
            response = requests.post(
                f"{self.url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": messages,
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
CSV_PATH = Path("posts.csv")
N_SHOTS = 3
QUERY = "Событие Росмолодёжи на острове Татышев"


def generate_post_text(query: str,
                       csv_path: Path = CSV_PATH,
                       n_shots: int = N_SHOTS,
                       ollama_url: str = OLLAMA_URL,
                       model: str = MODEL) -> str:
    shots: list[dict] = []
    try:
        shots = CSVExampleStore(csv_path).top_by_likes(
            n=n_shots, min_len=200, max_len=1500,
        )
    except FileNotFoundError:
        pass  

    builder = PromptBuilder()
    client = OllamaClient(url=ollama_url, model=model)
    messages = builder.build_prompt(query, shots)
    return client.generate(messages)


def main() -> None:
    store = CSVExampleStore(CSV_PATH)
    shots = store.top_by_likes(n=N_SHOTS, min_len=200, max_len=1500)

    builder = PromptBuilder()
    client = OllamaClient(url=OLLAMA_URL, model=MODEL)

    messages = builder.build_prompt(QUERY, shots)

    print(f"Ollama: {OLLAMA_URL} | model: {MODEL}")
    print(f"shots from CSV: {len(shots)} (likes: {[s['likes'] for s in shots]})")
    print(f"query> {QUERY}\n")
    print(f"bot> {client.generate(messages)}\n")


if __name__ == "__main__":
    main()
