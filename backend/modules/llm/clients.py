from abc import ABC, abstractmethod

import requests


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        raise NotImplementedError


class LLMError(RuntimeError):
    """Ошибка обращения к LLM."""
    pass


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
            raise LLMError(str(e)) from e
