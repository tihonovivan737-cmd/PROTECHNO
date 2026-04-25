import re
from abc import ABC, abstractmethod
from typing import Iterable, Optional

from backend.modules.profiles.registry import (
    Profile,
    get_profile,
    DEFAULT_PROFILE,
    YOUTH_CENTER,
)


STATE_MODIFIERS: dict[str, str] = {
    "CRISIS": (
        "\n\nДОПОЛНИТЕЛЬНО — СОСТОЯНИЕ СООБЩЕСТВА: КРИЗИС.\n"
        "Вовлечённость аудитории упала. Сделай пост максимально цепляющим: "
        "яркий заход, интрига, эмоциональный призыв к действию."
    ),
    "RISE": (
        "\n\nДОПОЛНИТЕЛЬНО — СОСТОЯНИЕ СООБЩЕСТВА: ПОДЪЁМ.\n"
        "Аудитория активна. Можно позволить более спокойный тон, "
        "но сохраняй вовлекающие элементы."
    ),
}


class BasePromptBuilder(ABC):
    @abstractmethod
    def build_prompt(
        self,
        query: str,
        shots: Iterable[dict] = (),
        profile: Optional[Profile] = None,
        state: Optional[str] = None,
    ) -> list[dict]:
        raise NotImplementedError


class PromptBuilder(BasePromptBuilder):

    @staticmethod
    def _brief_from_post(post_text: str, max_len: int = 120) -> str:
        first = re.split(r"(?<=[.!?…])\s", post_text, maxsplit=1)[0]
        return (first[:max_len] + "…") if len(first) > max_len else first

    def build_prompt(
        self,
        query: str,
        shots: Iterable[dict] = (),
        profile: Optional[Profile] = None,
        state: Optional[str] = None,
    ) -> list[dict]:
        if profile is None:
            profile = get_profile(DEFAULT_PROFILE) or YOUTH_CENTER

        system_text = profile.system
        if state and state in STATE_MODIFIERS:
            system_text += STATE_MODIFIERS[state]

        messages: list[dict] = [{"role": "system", "content": system_text}]

        messages.append({"role": "user", "content": f"Описание события:\n{profile.example_input}"})
        messages.append({"role": "assistant", "content": profile.example_output})

        for shot in shots:
            brief = self._brief_from_post(shot["text"])
            messages.append({"role": "user", "content": f"Описание события:\n{brief}"})
            messages.append({"role": "assistant", "content": shot["text"]})

        messages.append({"role": "user", "content": f"Описание события:\n{query.strip()}"})
        return messages
