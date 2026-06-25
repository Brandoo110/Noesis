from dataclasses import dataclass
from typing import Protocol, TypedDict

import httpx

from noesis.graph.errors import LLMUnavailableError, ResearchNodeError


class ChatMessage(TypedDict):
    role: str
    content: str


class ChatRequest(TypedDict):
    model: str
    messages: list[ChatMessage]
    temperature: float


class LLMProvider(Protocol):
    model_id: str

    def available(self) -> bool: ...

    def complete_text(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class ChatProviderConfig:
    api_key: str | None
    model_id: str
    endpoint: str
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class StaticLLMProvider:
    text: str
    model_id: str = "static"

    def available(self) -> bool:
        return True

    def complete_text(self, prompt: str) -> str:
        return self.text


class HttpLLMProvider:
    def __init__(self, config: ChatProviderConfig) -> None:
        self.config = config
        self.model_id = config.model_id

    def available(self) -> bool:
        return bool(self.config.api_key)

    def complete_text(self, prompt: str) -> str:
        if not self.config.api_key:
            raise LLMUnavailableError("LLM API key is not configured", reason="missing_key")
        payload: ChatRequest = {
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        try:
            response = httpx.post(
                self.config.endpoint,
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ResearchNodeError("LLM provider request failed", reason="request_failed") from exc
        return _extract_chat_content(response.json())


def make_deepseek_provider(
    api_key: str | None, model: str, endpoint: str
) -> HttpLLMProvider:
    return HttpLLMProvider(
        ChatProviderConfig(
            api_key=api_key,
            model_id=model,
            endpoint=endpoint,
        )
    )


def make_light_provider(
    api_key: str | None, model: str, endpoint: str
) -> HttpLLMProvider:
    return HttpLLMProvider(
        ChatProviderConfig(
            api_key=api_key,
            model_id=model,
            endpoint=endpoint,
        )
    )


def make_risk_provider(
    api_key: str | None, model: str, endpoint: str
) -> HttpLLMProvider:
    return HttpLLMProvider(
        ChatProviderConfig(
            api_key=api_key,
            model_id=model,
            endpoint=endpoint,
        )
    )


def _extract_chat_content(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ResearchNodeError("LLM provider returned invalid payload", reason="bad_payload")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ResearchNodeError("LLM provider returned no choices", reason="empty_choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ResearchNodeError("LLM provider returned invalid choice", reason="bad_choice")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ResearchNodeError("LLM provider returned invalid message", reason="bad_message")
    content = message.get("content")
    if not isinstance(content, str):
        raise ResearchNodeError("LLM provider returned no content", reason="empty_content")
    return content
