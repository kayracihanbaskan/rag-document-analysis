# LLM katmani: OpenRouter uzerinden OpenAI-uyumlu API cagiriyoruz.
# OpenRouter "openai/gpt-4o-mini" gibi model adlariyla birden fazla saglayiciyi
# tek bir OpenAI SDK ile kullanmamizi saglar.

from collections.abc import Iterator

from openai import OpenAI

from app.core.config import Settings


class OpenRouterLLM:
    """OpenRouter uzerinden chat completion."""

    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
        self._model = settings.llm_model

    def complete(self, system: str, user: str) -> str:
        """Tek seferde tam yanit dondurur."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def stream(self, system: str, user: str) -> Iterator[str]:
        """Token token uretir; SSE ile frontend'e iletecegiz."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


def get_llm(settings: Settings) -> OpenRouterLLM:
    return OpenRouterLLM(settings)
