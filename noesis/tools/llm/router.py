import json
import os
from collections.abc import Mapping
from enum import Enum
from typing import TypeVar

from pydantic import BaseModel, ValidationError

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
    def from_env(cls) -> "LLMRouter":
        return cls(
            providers={
                LLMRole.LIGHT: make_light_provider(os.getenv("LIGHT_LLM_API_KEY")),
                LLMRole.SYNTH: make_deepseek_provider(os.getenv("DEEPSEEK_API_KEY")),
                LLMRole.RISK: make_risk_provider(os.getenv("RISK_LLM_API_KEY")),
            }
        )

    def complete_json(
        self, role: LLMRole, prompt: str, schema: type[ModelT]
    ) -> ModelT:
        text = self.complete_text(role, prompt)
        try:
            payload: object = json.loads(text)
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
