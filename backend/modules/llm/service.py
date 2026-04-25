from pathlib import Path
from typing import Optional

from backend.app.config import settings
from backend.modules.llm.clients import LLMError, OllamaClient
from backend.modules.llm.example_store import CSVExampleStore
from backend.modules.llm.prompt_builder import PromptBuilder


def generate_post_text(
    query: str,
    n_shots: Optional[int] = None,
    model: Optional[str] = None,
    csv_path: Optional[Path] = None,
) -> tuple[str, str, int]:
    """
    Генерирует текст поста через Ollama с few-shot-примерами из CSV.
    Возвращает (text, model_name, shots_used).
    Бросает LLMError при ошибках LLM.
    """

    n_shots = settings.LLM_N_SHOTS if n_shots is None else n_shots
    model_name = model or settings.OLLAMA_MODEL
    examples_path = csv_path or settings.llm_examples_csv_abs

    shots: list[dict] = []
    if n_shots > 0:
        try:
            shots = CSVExampleStore(examples_path).top_by_likes(
                n=n_shots,
                min_len=settings.LLM_SHOT_MIN_LEN,
                max_len=settings.LLM_SHOT_MAX_LEN,
            )
        except FileNotFoundError:
            shots = []

    builder = PromptBuilder()
    client = OllamaClient(
        url=settings.OLLAMA_URL,
        model=model_name,
        timeout=settings.OLLAMA_TIMEOUT,
    )
    messages = builder.build_prompt(query, shots)
    text = client.generate(messages)
    return text, model_name, len(shots)


__all__ = ["generate_post_text", "LLMError"]
