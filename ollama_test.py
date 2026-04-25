from abc import ABC, abstractmethod
import requests

class BaseLLMClient(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

class PromptBuilder:

    def build(self, query: str) -> str:
        return f"""
        Ты редактор постов для медиасообщества для молодёжных ивентов.
        Тебе подаётся краткое описание события. Ты должен преобразовать его
        в готовый пост: грамотно, красиво, с цепляющим заголовком и эмодзи,
        чтобы завлечь аудиторию. Не выдумывай факты, которых нет в описании.

        Описание события:
        {query}

        Готовый пост:
        """.strip()


class OllamaClient(BaseLLMClient):

    def __init__(self, url: str, model: str, timeout: int = 120):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.8,
                        "top_k": 20,
                        "repeat_penalty": 1.05,
                        "num_predict": 512,
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
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

    prompt = builder.build(QUERY)
    answer = client.generate(prompt)

    print(f"bot> {answer}\n")


if __name__ == "__main__":
    main()