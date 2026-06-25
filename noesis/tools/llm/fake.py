import json
from collections.abc import Mapping, Set

from pydantic import BaseModel, ValidationError

from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.tools.llm.router import LLMRole, ModelT


class FakeLLMRouter:
    def __init__(
        self,
        *,
        json_by_role: Mapping[LLMRole, object] | None = None,
        text_by_role: Mapping[LLMRole, str] | None = None,
        available_roles: Set[LLMRole] | None = None,
    ) -> None:
        self.json_by_role = dict(json_by_role or {})
        self.text_by_role = dict(text_by_role or {})
        self.available_roles = set(available_roles) if available_roles is not None else None

    def complete_json(
        self, role: LLMRole, prompt: str, schema: type[ModelT]
    ) -> ModelT:
        payload = self.json_by_role.get(role)
        if payload is None:
            text = self.text_by_role.get(role)
            if text is None:
                raise LLMUnavailableError("Fake LLM role is not configured", reason="missing_role")
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ResearchNodeError("Fake LLM returned invalid JSON", reason="invalid_json") from exc
        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            raise ResearchNodeError(
                "Fake LLM JSON failed schema validation",
                reason="schema_validation_failed",
            ) from exc

    def complete_text(self, role: LLMRole, prompt: str) -> str:
        text = self.text_by_role.get(role)
        if text is None:
            raise LLMUnavailableError("Fake LLM role is not configured", reason="missing_role")
        return text

    def available(self, role: LLMRole) -> bool:
        if self.available_roles is not None:
            return role in self.available_roles
        return role in self.json_by_role or role in self.text_by_role
