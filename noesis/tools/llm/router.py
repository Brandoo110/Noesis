import json
from collections.abc import Mapping
from enum import Enum
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from noesis.config.settings import Settings
from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.tools.llm.providers import (
    LLMProvider,
    make_deepseek_provider,
    make_light_provider,
    make_risk_provider,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMRole(str, Enum):
    LIGHT = "light"
    SYNTH = "synth"
    RISK = "risk"


class LLMRouter:
    def __init__(self, providers: Mapping[LLMRole, LLMProvider] | None = None) -> None:
        self.providers = dict(providers or {})

    @classmethod
    def from_env(cls, settings: Settings | None = None) -> "LLMRouter":
        resolved = settings or Settings()
        return cls(
            providers={
                LLMRole.LIGHT: make_light_provider(
                    resolved.light_llm_api_key,
                    resolved.light_model,
                    resolved.light_endpoint,
                ),
                LLMRole.SYNTH: make_deepseek_provider(
                    resolved.deepseek_api_key,
                    resolved.deepseek_model,
                    resolved.deepseek_endpoint,
                ),
                LLMRole.RISK: make_risk_provider(
                    resolved.risk_llm_api_key,
                    resolved.risk_model,
                    resolved.risk_endpoint,
                ),
            }
        )

    def complete_json(
        self, role: LLMRole, prompt: str, schema: type[ModelT]
    ) -> ModelT:
        text = self.complete_text(role, _json_prompt(prompt, schema))
        try:
            payload: object = json.loads(_strip_json_fence(text))
        except json.JSONDecodeError as exc:
            raise ResearchNodeError("LLM returned invalid JSON", reason="invalid_json") from exc
        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            raise ResearchNodeError(
                "LLM JSON failed schema validation",
                reason="schema_validation_failed",
            ) from exc

    def complete_text(self, role: LLMRole, prompt: str) -> str:
        provider = self.providers.get(role)
        if provider is None:
            raise LLMUnavailableError("LLM provider is not configured", reason="missing_provider")
        if not provider.available():
            raise LLMUnavailableError("LLM provider is unavailable", reason="missing_key")
        return provider.complete_text(prompt)

    def available(self, role: LLMRole) -> bool:
        provider = self.providers.get(role)
        return provider is not None and provider.available()


def _json_prompt(prompt: str, schema: type[BaseModel]) -> str:
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, sort_keys=True)
    return (
        f"{prompt}\n\n"
        "Return only valid JSON that conforms to this JSON Schema. "
        "Do not include markdown fences or explanatory text.\n"
        f"JSON Schema:\n{schema_json}"
    )


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped
