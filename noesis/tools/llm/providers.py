from dataclasses import dataclass
from time import sleep
from typing import Protocol, TypedDict

import httpx

from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.tools.contracts import ToolUsage


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
class LLMUsage:
    token_input: int = 0
    token_output: int = 0
    estimated_cost_usd: float = 0.0

    def to_tool_usage(self) -> ToolUsage:
        return ToolUsage(
            token_input=self.token_input,
            token_output=self.token_output,
            estimated_cost_usd=self.estimated_cost_usd,
        )


@dataclass(frozen=True)
class LLMCompletion:
    text: str
    usage: LLMUsage = LLMUsage()


@dataclass(frozen=True)
class ChatProviderConfig:
    api_key: str | None
    model_id: str
    endpoint: str
    timeout_seconds: float = 60.0
    retry_backoff_seconds: tuple[float, ...] = (0.5, 1.0)
    transport: httpx.BaseTransport | None = None
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0


@dataclass(frozen=True)
class StaticLLMProvider:
    text: str
    model_id: str = "static"

    def available(self) -> bool:
        return True

    def complete_text(self, prompt: str) -> str:
        return self.text

    def complete_text_with_usage(self, prompt: str) -> LLMCompletion:
        return LLMCompletion(text=self.text)


class HttpLLMProvider:
    def __init__(self, config: ChatProviderConfig) -> None:
        self.config = config
        self.model_id = config.model_id

    def available(self) -> bool:
        return bool(self.config.api_key)

    def complete_text(self, prompt: str) -> str:
        return self.complete_text_with_usage(prompt).text

    def complete_text_with_usage(self, prompt: str) -> LLMCompletion:
        if not self.config.api_key:
            raise LLMUnavailableError("LLM API key is not configured", reason="missing_key")
        payload: ChatRequest = {
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        response = self._post_with_retries(payload, headers)
        response_payload = response.json()
        return LLMCompletion(
            text=_extract_chat_content(response_payload),
            usage=_extract_usage(response_payload, self.config),
        )

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
    api_key: str | None,
    model: str,
    endpoint: str,
    *,
    input_cost_per_million: float = 0.0,
    output_cost_per_million: float = 0.0,
) -> HttpLLMProvider:
    return HttpLLMProvider(
        ChatProviderConfig(
            api_key=api_key,
            model_id=model,
            endpoint=endpoint,
            input_cost_per_million=input_cost_per_million,
            output_cost_per_million=output_cost_per_million,
        )
    )


def make_light_provider(
    api_key: str | None,
    model: str,
    endpoint: str,
    *,
    input_cost_per_million: float = 0.0,
    output_cost_per_million: float = 0.0,
) -> HttpLLMProvider:
    return HttpLLMProvider(
        ChatProviderConfig(
            api_key=api_key,
            model_id=model,
            endpoint=endpoint,
            input_cost_per_million=input_cost_per_million,
            output_cost_per_million=output_cost_per_million,
        )
    )


def make_risk_provider(
    api_key: str | None,
    model: str,
    endpoint: str,
    *,
    input_cost_per_million: float = 0.0,
    output_cost_per_million: float = 0.0,
) -> HttpLLMProvider:
    return HttpLLMProvider(
        ChatProviderConfig(
            api_key=api_key,
            model_id=model,
            endpoint=endpoint,
            input_cost_per_million=input_cost_per_million,
            output_cost_per_million=output_cost_per_million,
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


def _extract_usage(payload: object, config: ChatProviderConfig) -> LLMUsage:
    if not isinstance(payload, dict):
        return LLMUsage()
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return LLMUsage()
    token_input = _int_field(usage, "prompt_tokens", "input_tokens")
    token_output = _int_field(usage, "completion_tokens", "output_tokens")
    total_tokens = _int_field(usage, "total_tokens")
    if token_output == 0 and total_tokens > token_input:
        token_output = total_tokens - token_input
    cost = (
        (token_input / 1_000_000) * config.input_cost_per_million
        + (token_output / 1_000_000) * config.output_cost_per_million
    )
    return LLMUsage(
        token_input=token_input,
        token_output=token_output,
        estimated_cost_usd=round(cost, 6),
    )


def _int_field(payload: dict[object, object], *keys: str) -> int:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, float):
            return max(0, int(value))
    return 0
