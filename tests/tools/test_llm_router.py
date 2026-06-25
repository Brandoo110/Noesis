import pytest
from pydantic import BaseModel

from noesis.graph.errors import ResearchNodeError
from noesis.tools.llm.providers import HttpLLMProvider
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.llm.providers import StaticLLMProvider
from noesis.tools.llm.router import LLMRole, LLMRouter


class LabelPayload(BaseModel):
    label: str


class CountPayload(BaseModel):
    count: int


def test_fake_llm_router_returns_preconfigured_role_outputs() -> None:
    router = FakeLLMRouter(
        json_by_role={LLMRole.LIGHT: {"label": "ok"}},
        text_by_role={LLMRole.SYNTH: "deep synthesis"},
    )

    payload = router.complete_json(LLMRole.LIGHT, "extract", LabelPayload)
    text = router.complete_text(LLMRole.SYNTH, "summarize")

    assert router.available(LLMRole.LIGHT)
    assert router.available(LLMRole.SYNTH)
    assert payload == LabelPayload(label="ok")
    assert text == "deep synthesis"


def test_llm_router_reports_synth_unavailable_without_deepseek_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    router = LLMRouter.from_env()

    assert not router.available(LLMRole.SYNTH)


def test_llm_router_from_env_maps_configured_provider_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIGHT_LLM_API_KEY", "light-key")
    monkeypatch.setenv("LIGHT_ENDPOINT", "https://light.example/chat")
    monkeypatch.setenv("LIGHT_MODEL", "glm-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deep-key")
    monkeypatch.setenv("DEEPSEEK_ENDPOINT", "https://deep.example/chat")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deep-test")
    monkeypatch.setenv("RISK_LLM_API_KEY", "risk-key")
    monkeypatch.setenv("RISK_ENDPOINT", "https://risk.example/chat")
    monkeypatch.setenv("RISK_MODEL", "gemini-test")

    router = LLMRouter.from_env()

    light = router.providers[LLMRole.LIGHT]
    synth = router.providers[LLMRole.SYNTH]
    risk = router.providers[LLMRole.RISK]
    assert isinstance(light, HttpLLMProvider)
    assert isinstance(synth, HttpLLMProvider)
    assert isinstance(risk, HttpLLMProvider)
    assert light.model_id == "glm-test"
    assert synth.model_id == "deep-test"
    assert risk.model_id == "gemini-test"
    assert light.config.endpoint == "https://light.example/chat"
    assert synth.config.endpoint == "https://deep.example/chat"
    assert risk.config.endpoint == "https://risk.example/chat"


def test_llm_router_complete_json_validates_schema() -> None:
    router = LLMRouter(
        providers={LLMRole.LIGHT: StaticLLMProvider('{"label": "ok"}')}
    )

    payload = router.complete_json(LLMRole.LIGHT, "extract", LabelPayload)

    assert payload == LabelPayload(label="ok")


def test_llm_router_complete_json_raises_on_schema_mismatch() -> None:
    router = LLMRouter(
        providers={LLMRole.RISK: StaticLLMProvider('{"count": "bad"}')}
    )

    with pytest.raises(ResearchNodeError):
        router.complete_json(LLMRole.RISK, "review", CountPayload)
