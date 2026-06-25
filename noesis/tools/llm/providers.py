from dataclasses import dataclass
from time import sleep
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
    timeout_seconds: float = 60.0
    retry_backoff_seconds: tuple[float, ...] = (0.5, 1.0)
    transport: httpx.BaseTransport | None = None


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
        response = self._post_with_retries(payload, headers)
        return _extract_chat_content(response.json())

    def _post_with_retries(
        self, payload: ChatRequest, headers: dict[str, str]
    ) -> httpx.Response:
        attempts = len(self.config.retry_backoff_seconds) + 1
        last_error: httpx.HTTPError | None = None
        client = self._client()
        try:
            for attempt_index in range(attempts):
                try:
                    response = self._post(payload, headers, client)
                    response.raise_for_status()
                    return response
                except (httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                    last_error = exc
                except httpx.HTTPStatusError as exc:
                    if not _is_retryable_status(exc):
                        raise _request_failed(exc) from exc
                    last_error = exc
                except httpx.HTTPError as exc:
                    raise _request_failed(exc) from exc
                if attempt_index < attempts - 1:
                    delay = self.config.retry_backoff_seconds[attempt_index]
                    if delay > 0:
                        sleep(delay)
        finally:
            if client is not None:
                client.close()
        raise _request_failed(last_error) from last_error

    def _post(
        self,
        payload: ChatRequest,
        headers: dict[str, str],
        client: httpx.Client | None,
    ) -> httpx.Response:
        if client is not None:
            return client.post(
                self.config.endpoint,
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
        return httpx.post(
            self.config.endpoint,
            json=payload,
            headers=headers,
            timeout=self.config.timeout_seconds,
        )

    def _client(self) -> httpx.Client | None:
        if self.config.transport is None:
            return None
        return httpx.Client(transport=self.config.transport)


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


def _is_retryable_status(exc: httpx.HTTPStatusError) -> bool:
    return exc.response.status_code >= 500


def _request_failed(exc: httpx.HTTPError | None) -> ResearchNodeError:
    return ResearchNodeError("LLM provider request failed", reason="request_failed")


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
