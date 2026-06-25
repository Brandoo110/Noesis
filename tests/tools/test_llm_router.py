import pytest
from pydantic import BaseModel

from noesis.graph.errors import ResearchNodeError
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
