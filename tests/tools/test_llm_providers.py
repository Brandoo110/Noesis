import httpx
import pytest

from noesis.graph.errors import ResearchNodeError
from noesis.tools.llm.providers import (
    ChatProviderConfig,
    HttpLLMProvider,
    make_deepseek_provider,
    make_light_provider,
    make_risk_provider,
)


def test_providers_use_configured_models_and_endpoints() -> None:
    light = make_light_provider("light-key", "glm-test", "https://light.example/chat")
    synth = make_deepseek_provider("deep-key", "deep-test", "https://deep.example/chat")
    risk = make_risk_provider("risk-key", "gemini-test", "https://risk.example/chat")

    assert isinstance(light, HttpLLMProvider)
    assert isinstance(synth, HttpLLMProvider)
    assert isinstance(risk, HttpLLMProvider)
    assert light.model_id == "glm-test"
    assert synth.model_id == "deep-test"
    assert risk.model_id == "gemini-test"
    assert light.config.endpoint == "https://light.example/chat"
    assert synth.config.endpoint == "https://deep.example/chat"
    assert risk.config.endpoint == "https://risk.example/chat"
    assert light.config.timeout_seconds == 60.0


def test_provider_is_unavailable_without_key() -> None:
    provider = make_deepseek_provider("", "deep-test", "https://deep.example/chat")

    assert not provider.available()


def test_http_provider_retries_timeout_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("slow response", request=request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
            request=request,
        )

    provider = HttpLLMProvider(
        ChatProviderConfig(
            api_key="key",
            model_id="model",
            endpoint="https://llm.example/chat",
            retry_backoff_seconds=(0.0,),
            transport=httpx.MockTransport(handler),
        )
    )

    assert provider.complete_text("prompt") == "ok"
    assert calls == 2


def test_http_provider_extracts_usage_and_estimated_cost() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 500,
                },
            },
            request=request,
        )

    provider = HttpLLMProvider(
        ChatProviderConfig(
            api_key="key",
            model_id="model",
            endpoint="https://llm.example/chat",
            input_cost_per_million=1.0,
            output_cost_per_million=2.0,
            transport=httpx.MockTransport(handler),
        )
    )

    completion = provider.complete_text_with_usage("prompt")

    assert completion.text == "ok"
    assert completion.usage.token_input == 1000
    assert completion.usage.token_output == 500
    assert completion.usage.estimated_cost_usd == 0.002


def test_http_provider_retries_5xx_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(502, request=request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
            request=request,
        )

    provider = HttpLLMProvider(
        ChatProviderConfig(
            api_key="key",
            model_id="model",
            endpoint="https://llm.example/chat",
            retry_backoff_seconds=(0.0,),
            transport=httpx.MockTransport(handler),
        )
    )

    assert provider.complete_text("prompt") == "ok"
    assert calls == 2


def test_http_provider_raises_after_persistent_transient_failures() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("connection timeout", request=request)

    provider = HttpLLMProvider(
        ChatProviderConfig(
            api_key="key",
            model_id="model",
            endpoint="https://llm.example/chat",
            retry_backoff_seconds=(0.0, 0.0),
            transport=httpx.MockTransport(handler),
        )
    )

    with pytest.raises(ResearchNodeError) as exc_info:
        provider.complete_text("prompt")

    assert exc_info.value.reason == "request_failed"
    assert calls == 3
