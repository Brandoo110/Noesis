from noesis.tools.llm.providers import (
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


def test_provider_is_unavailable_without_key() -> None:
    provider = make_deepseek_provider("", "deep-test", "https://deep.example/chat")

    assert not provider.available()
