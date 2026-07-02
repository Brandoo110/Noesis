from __future__ import annotations

import json

from pydantic import ValidationError

from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.graph.schemas import EvidenceRecord, IngestedDoc
from noesis.tools.contracts import ToolCallRequest
from noesis.tools.execution import ToolExecutionError, ToolExecutor
from noesis.tools.llm.router import LLMRole, ModelT
from noesis.tools.search.base import SearchAdapter


class ToolAwareSearchAdapter:
    def __init__(
        self,
        adapter: SearchAdapter,
        executor: ToolExecutor,
        *,
        default_run_id: str = "unscoped",
    ) -> None:
        self.adapter = adapter
        self.executor = executor
        self.default_run_id = default_run_id

    def with_run_id(self, run_id: str) -> ToolAwareSearchAdapter:
        return ToolAwareSearchAdapter(self.adapter, self.executor, default_run_id=run_id)

    def search(
        self, query: str, *, limit: int = 8, run_id: str | None = None
    ) -> list[IngestedDoc]:
        request = ToolCallRequest(
            run_id=run_id or self.default_run_id,
            input_summary=f"query={query[:160]} limit={limit}",
            cache_key=f"search.tavily:{query}:{limit}",
        )
        try:
            return self.executor.execute(
                "search.tavily",
                request,
                lambda: self.adapter.search(query, limit=limit),
                serialize_result=_dump_ingested_docs,
                deserialize_result=_load_ingested_docs,
                summarize_result=lambda result: f"{len(result)} docs",
            )
        except ToolExecutionError as exc:
            _raise_original(exc)


class ToolAwareLLMRouter:
    def __init__(
        self,
        router: object,
        executor: ToolExecutor,
        *,
        default_run_id: str = "unscoped",
    ) -> None:
        self.router = router
        self.executor = executor
        self.default_run_id = default_run_id

    def with_run_id(self, run_id: str) -> ToolAwareLLMRouter:
        return ToolAwareLLMRouter(self.router, self.executor, default_run_id=run_id)

    def available(self, role: LLMRole) -> bool:
        return bool(self.router.available(role))

    def complete_text(
        self, role: LLMRole, prompt: str, *, run_id: str | None = None
    ) -> str:
        request = ToolCallRequest(
            run_id=run_id or self.default_run_id,
            input_summary=f"role={role.value} prompt_chars={len(prompt)}",
        )
        try:
            return self.executor.execute(
                f"llm.{role.value}",
                request,
                lambda: self.router.complete_text(role, prompt),
                summarize_result=lambda result: f"text_chars={len(result)}",
            )
        except ToolExecutionError as exc:
            _raise_original(exc)

    def complete_json(
        self,
        role: LLMRole,
        prompt: str,
        schema: type[ModelT],
        *,
        run_id: str | None = None,
    ) -> ModelT:
        request = ToolCallRequest(
            run_id=run_id or self.default_run_id,
            input_summary=f"role={role.value} schema={schema.__name__}",
        )
        try:
            return self.executor.execute(
                f"llm.{role.value}",
                request,
                lambda: self.router.complete_json(role, prompt, schema),
                summarize_result=lambda result: f"schema={result.__class__.__name__}",
            )
        except ToolExecutionError as exc:
            _raise_original(exc)


class ToolAwareEvidenceRetriever:
    def __init__(
        self,
        retriever: object,
        executor: ToolExecutor,
        *,
        default_run_id: str = "unscoped",
    ) -> None:
        self.retriever = retriever
        self.executor = executor
        self.default_run_id = default_run_id

    def with_run_id(self, run_id: str) -> ToolAwareEvidenceRetriever:
        return ToolAwareEvidenceRetriever(
            self.retriever,
            self.executor,
            default_run_id=run_id,
        )

    def index(self, evidences: list[EvidenceRecord]) -> None:
        self.retriever.index(evidences)

    def retrieve(
        self,
        query: str,
        *,
        run_id: str,
        top_k: int = 6,
    ) -> list[EvidenceRecord]:
        request = ToolCallRequest(
            run_id=run_id or self.default_run_id,
            input_summary=f"query={query[:160]} top_k={top_k}",
            cache_key=f"retrieval.evidence:{run_id}:{query}:{top_k}",
        )
        try:
            return self.executor.execute(
                "retrieval.evidence",
                request,
                lambda: self.retriever.retrieve(query, run_id=run_id, top_k=top_k),
                serialize_result=_dump_evidence_records,
                deserialize_result=_load_evidence_records,
                summarize_result=lambda result: f"{len(result)} evidences",
            )
        except ToolExecutionError as exc:
            _raise_original(exc)


def _dump_ingested_docs(docs: list[IngestedDoc]) -> str:
    return json.dumps([item.model_dump(mode="json") for item in docs], sort_keys=True)


def _load_ingested_docs(raw: str) -> list[IngestedDoc]:
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValidationError.from_exception_data("IngestedDocList", [])
    return [IngestedDoc.model_validate(item) for item in payload]


def _dump_evidence_records(records: list[EvidenceRecord]) -> str:
    return json.dumps([item.model_dump(mode="json") for item in records], sort_keys=True)


def _load_evidence_records(raw: str) -> list[EvidenceRecord]:
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValidationError.from_exception_data("EvidenceRecordList", [])
    return [EvidenceRecord.model_validate(item) for item in payload]


def _raise_original(exc: ToolExecutionError) -> None:
    if isinstance(exc.original, (LLMUnavailableError, ResearchNodeError)):
        raise exc.original
    if exc.original is not None:
        raise exc.original
    raise exc
