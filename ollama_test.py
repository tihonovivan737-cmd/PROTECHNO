from abc import ABC, abstractmethod
import requests
import re
from pathlib import Path
from types import ModuleType
from typing import Iterable
import csv

import profile_youth_center
import profile_volunteers

# Реестр доступных профилей площадок (системный промпт + few-shot пример).
PROFILES: dict[str, ModuleType] = {
    profile_youth_center.NAME: profile_youth_center,
    profile_volunteers.NAME: profile_volunteers,
}
DEFAULT_PROFILE = profile_youth_center.NAME
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
    """Собирает chat-messages для LLM на основе выбранного профиля площадки.

    Профиль (см. `profile_youth_center.py`, `profile_volunteers.py`)
    задаёт системный промпт и пример входа/выхода для few-shot.
    """

    def __init__(self, profile: ModuleType | str | None = None):
        if profile is None:
            profile = DEFAULT_PROFILE
        if isinstance(profile, str):
            if profile not in PROFILES:
                raise ValueError(
                    f"Неизвестный профиль: {profile!r}. "
                    f"Доступные: {sorted(PROFILES)}"
                )
            profile = PROFILES[profile]
        self.profile = profile

    @property
    def EXAMPLE_INPUT(self) -> str:
        return self.profile.EXAMPLE_INPUT

    @property
    def EXAMPLE_OUTPUT(self) -> str:
        return self.profile.EXAMPLE_OUTPUT

    @property
    def SYSTEM(self) -> str:
        return self.profile.SYSTEM

    # Модификаторы тона в зависимости от состояния сообщества (см. condition.py)
    STATE_MODIFIERS = {
        "CRISIS": (            "\n\nТЕКУЩЕЕ СОСТОЯНИЕ СООБЩЕСТВА: CRISIS (вовлечённость низкая).\n"
            "- Тон сдержанный, спокойный, уважительный, без громких призывов и восклицаний.\n"
            "- Минимум эмодзи (0–1), без капса, без агрессивного маркетинга.\n"
            "- Делай акцент на пользе, заботе и поддержке аудитории.\n"
            "- Призыв к действию мягкий, ненавязчивый."
        ),
        "NORMAL": (
            "\n\nТЕКУЩЕЕ СОСТОЯНИЕ СООБЩЕСТВА: NORMAL (вовлечённость стабильная).\n"
            "- Тон обычный — дружелюбный и тёплый, как в базовом стиле.\n"
            "- Эмодзи 1–3, призыв к действию уверенный, но не давящий."
        ),
        "RISE": (
            "\n\nТЕКУЩЕЕ СОСТОЯНИЕ СООБЩЕСТВА: RISE (вовлечённость растёт).\n"
            "- Тон активный, энергичный, праздничный — лови волну.\n"
            "- Эмодзи 2–4, можно яркие сравнения и эмоциональные акценты.\n"
            "- Призыв к действию громкий и заметный, подталкивай делиться и звать друзей."
        ),
    }

    def system_for_state(self, state: str | None) -> str:
        if not state:
            return self.SYSTEM
        modifier = self.STATE_MODIFIERS.get(state.upper())
        return self.SYSTEM + modifier if modifier else self.SYSTEM

    @staticmethod
    def _brief_from_post(post_text: str, max_len: int = 120) -> str:
        first = re.split(r"(?<=[.!?…])\s", post_text, maxsplit=1)[0]
        return (first[:max_len] + "…") if len(first) > max_len else first
    def build_prompt(self, query: str, shots: Iterable[dict] = (), state: str | None = None) -> list[dict]:
        messages = [{"role": "system", "content": self.system_for_state(state)}]
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

<<<<<<< HEAD
def generate_post_text(
    query: str,
    state: str | None = None,
    profile: ModuleType | str | None = None,
) -> str:
    """Генерирует текст поста по описанию события через Ollama.

    `state` — текущее состояние сообщества: "CRISIS" / "NORMAL" / "RISE".
        Если задано, в системный промпт добавляется соответствующий модификатор тона.
    `profile` — имя профиля площадки (см. `PROFILES`) или сам модуль профиля.
        По умолчанию используется `DEFAULT_PROFILE` (молодёжный центр).
    """
    store = CSVExampleStore(CSV_PATH)
    shots = store.top_by_likes(n=N_SHOTS, min_len=200, max_len=1500)

    builder = PromptBuilder(profile=profile)
    client = OllamaClient(url=OLLAMA_URL, model=MODEL)

    messages = builder.build_prompt(query, shots, state=state)
    return client.generate(messages)
=======

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


>>>>>>> 91e5689333a409e238139bceff41d8d3aa4de8df
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
