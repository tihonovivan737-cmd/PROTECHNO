import re
from abc import ABC, abstractmethod
from typing import Iterable


class BasePromptBuilder(ABC):
    @abstractmethod
    def build_prompt(self, query: str, shots: Iterable[dict] = ()) -> list[dict]:
        raise NotImplementedError


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
        messages: list[dict] = [{"role": "system", "content": self.SYSTEM}]

        messages.append({"role": "user", "content": f"Описание события:\n{self.EXAMPLE_INPUT}"})
        messages.append({"role": "assistant", "content": self.EXAMPLE_OUTPUT})

        for shot in shots:
            brief = self._brief_from_post(shot["text"])
            messages.append({"role": "user", "content": f"Описание события:\n{brief}"})
            messages.append({"role": "assistant", "content": shot["text"]})

        messages.append({"role": "user", "content": f"Описание события:\n{query.strip()}"})
        return messages
