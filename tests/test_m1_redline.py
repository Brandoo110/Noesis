import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from noesis.api.app import create_app
from noesis.api.deps import _checkpoint_path, get_graph_deps
from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.db.repos.node_traces_repo import NodeTracesRepo
from noesis.graph.errors import IngestError
from noesis.graph.runner import build_graph_deps
from noesis.graph.schemas import IngestedDoc
from noesis.tools.llm.router import LLMRole
from noesis.tools.search.base import SearchAdapter
from noesis.tools.search.fake import FakeSearchAdapter

NOW = "2026-06-26T00:00:00Z"


@dataclass(frozen=True)
class ScenarioContext:
    client: TestClient
    db_path: Path


@pytest.mark.parametrize("mode", ("redline_summary", "redline_assumption"))
def test_redline_thesis_is_not_persisted(tmp_path: Path, mode: str) -> None:
    with _client(tmp_path, llm=ScenarioFakeLLM(mode)) as ctx:
        run_id, payload = _run_to_completion(ctx)

        conn = connect(ctx.db_path)
        try:
            thesis_count = _count(conn, "SELECT COUNT(*) FROM theses WHERE run_id = ?", run_id)
        finally:
            conn.close()

    assert payload["status"] == "completed"
    assert payload["thesis_id"] is None
    assert thesis_count == 0


def test_grounding_filters_intel_with_unknown_evidence_id(tmp_path: Path) -> None:
    with _client(tmp_path, llm=ScenarioFakeLLM("bad_intel_evidence")) as ctx:
        run_id, payload = _run_to_completion(ctx)

        conn = connect(ctx.db_path)
        try:
            intel_count = _count(
                conn,
                "SELECT COUNT(*) FROM intel_items WHERE run_id = ?",
                run_id,
            )
        finally:
            conn.close()

    assert payload["status"] == "completed"
    assert intel_count == 0


def test_grounding_blocks_thesis_with_no_evidence_assumptions(
    tmp_path: Path,
) -> None:
    with _client(tmp_path, llm=ScenarioFakeLLM("thesis_no_evidence")) as ctx:
        run_id, payload = _run_to_completion(ctx)

        conn = connect(ctx.db_path)
        try:
            thesis_count = _count(conn, "SELECT COUNT(*) FROM theses WHERE run_id = ?", run_id)
        finally:
            conn.close()

    assert payload["status"] == "completed"
    assert payload["thesis_id"] is None
    assert thesis_count == 0


def test_search_failure_completes_without_intel_and_records_degraded_trace(
    tmp_path: Path,
) -> None:
    with _client(
        tmp_path,
        llm=ScenarioFakeLLM("normal"),
        search=FailingSearchAdapter(),
    ) as ctx:
        run_id, payload = _run_to_completion(ctx)

        conn = connect(ctx.db_path)
        try:
            intel_count = _count(
                conn,
                "SELECT COUNT(*) FROM intel_items WHERE run_id = ?",
                run_id,
            )
            traces = NodeTracesRepo().list_by_run(run_id, conn=conn)
        finally:
            conn.close()

    assert payload["status"] == "completed"
    assert payload["thesis_id"] is None
    assert intel_count == 0
    assert any(trace.status == "degraded" for trace in traces)


class ScenarioFakeLLM:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def available(self, role: LLMRole) -> bool:
        return True

    def complete_json(
        self, role: LLMRole, prompt: str, schema: type[BaseModel]
    ) -> BaseModel:
        if schema.__name__ == "ResolvedEntity":
            return schema.model_validate(
                {
                    "entity_id": "entity-aapl",
                    "node_type": "company",
                    "name": "Apple Inc.",
                    "aliases": ["AAPL"],
                    "identifiers": {"symbol": "AAPL"},
                    "market": "US",
                }
            )
        evidence_id = _first_evidence_id(prompt)
        if schema.__name__ == "IntelSynthPayload":
            return schema.model_validate(
                {"items": _intel_items(evidence_id, self.mode)}
            )
        if schema.__name__ == "ExpandPayload":
            return schema.model_validate(_edge_payload(evidence_id))
        return schema.model_validate(_thesis_payload(evidence_id, self.mode))

    def complete_text(self, role: LLMRole, prompt: str) -> str:
        return "{}"


class FailingSearchAdapter:
    def search(self, query: str, *, limit: int = 8) -> list[IngestedDoc]:
        raise IngestError("search failed", reason="search_failed")


@contextmanager
def _client(
    tmp_path: Path,
    *,
    llm: ScenarioFakeLLM,
    search: SearchAdapter | None = None,
) -> Iterator[ScenarioContext]:
    db_path = tmp_path / "noesis.db"
    checkpoint_path = Path(_checkpoint_path(str(db_path)))
    chroma_dir = tmp_path / "chroma"
    app = create_app()

    def override_graph_deps() -> Iterator[object]:
        conn = connect(db_path)
        checkpoint_conn = sqlite3.connect(checkpoint_path, check_same_thread=False)
        try:
            migrate(conn)
            yield build_graph_deps(
                conn=conn,
                checkpoint_conn=checkpoint_conn,
                chroma_dir=str(chroma_dir),
                search=search or FakeSearchAdapter(_docs()),
                llm=llm,
                now=lambda: NOW,
            )
        finally:
            checkpoint_conn.close()
            conn.close()

    app.dependency_overrides[get_graph_deps] = override_graph_deps
    with TestClient(app, raise_server_exceptions=False) as client:
        yield ScenarioContext(client=client, db_path=db_path)


def _run_to_completion(ctx: ScenarioContext) -> tuple[str, dict[str, object]]:
    position = ctx.client.post(
        "/positions",
        json={"symbol": "AAPL", "market": "US", "name": "Apple", "kind": "owned"},
    )
    started = ctx.client.post(
        "/runs",
        json={"position_id": position.json()["id"]},
    )
    payload = started.json()
    thesis_id = payload.get("thesis_id")
    if payload["status"] == "awaiting_confirmation" and isinstance(thesis_id, str):
        confirmed = ctx.client.post(
            f"/theses/{thesis_id}/confirm",
            json={"status": "confirmed"},
        )
        return str(confirmed.json()["run_id"]), confirmed.json()
    return str(payload["run_id"]), payload


def _docs() -> list[IngestedDoc]:
    return [
        IngestedDoc(
            source="web",
            source_tier=2,
            title="Supplier update",
            url="https://example.com/supplier",
            text="Supplier pressure eased for Apple.",
        )
    ]


def _intel_items(evidence_id: str | None, mode: str) -> list[dict[str, object]]:
    if evidence_id is None:
        return []
    used_id = "evidence-missing" if mode == "bad_intel_evidence" else evidence_id
    return [
        {
            "title": "Supplier pressure update",
            "content": "Supplier pressure eased based on cited evidence.",
            "event_type": "supply_chain",
            "source": "web",
            "source_tier": 2,
            "url": "https://example.com/supplier",
            "published_at": None,
            "sentiment": {"dir": "neutral", "conf": 0.7},
            "evidence_ids": [used_id],
        }
    ]


def _edge_payload(evidence_id: str | None) -> dict[str, object]:
    if evidence_id is None:
        return {
            "edges": [
                {
                    "to_name": "Semiconductor Suppliers",
                    "to_symbol": None,
                    "to_node_type": "segment",
                    "relation": "belongs_to",
                    "basis": "inferred",
                    "confidence": 0.55,
                    "evidence_ids": [],
                    "rationale": "Apple participates in this supply-chain segment.",
                }
            ]
        }
    return {
        "edges": [
            {
                "to_name": "Taiwan Semiconductor Manufacturing",
                "to_symbol": "TSM",
                "to_node_type": "company",
                "relation": "supplier",
                "basis": "source_backed",
                "confidence": 0.82,
                "evidence_ids": [evidence_id],
                "rationale": "Supplier relationship is cited in evidence.",
            }
        ]
    }


def _thesis_payload(evidence_id: str | None, mode: str) -> dict[str, object]:
    if evidence_id is None:
        return {"summary": "No evidence-backed thesis.", "assumptions": []}
    if mode == "redline_summary":
        return _thesis("Consider buy action with 目标价位 language.", evidence_id)
    if mode == "redline_assumption":
        return {
            "summary": "Evidence suggests supplier pressure is easing.",
            "assumptions": [
                {
                    "text": "目标价 assumptions must not be persisted.",
                    "kind": "assumption",
                    "evidence_ids": [evidence_id],
                }
            ],
        }
    if mode == "thesis_no_evidence":
        return {
            "summary": "Evidence suggests supplier pressure is easing.",
            "assumptions": [
                {
                    "text": "Supplier pressure remains observable.",
                    "kind": "assumption",
                    "evidence_ids": [],
                }
            ],
        }
    return _thesis("Evidence suggests supplier pressure is easing.", evidence_id)


def _thesis(summary: str, evidence_id: str) -> dict[str, object]:
    return {
        "summary": summary,
        "assumptions": [
            {
                "text": "Supplier pressure remains observable in future filings.",
                "kind": "assumption",
                "evidence_ids": [evidence_id],
            }
        ],
    }


def _count(conn: sqlite3.Connection, sql: str, run_id: str) -> int:
    row = conn.execute(sql, (run_id,)).fetchone()
    return int(row[0])


def _first_evidence_id(prompt: str) -> str | None:
    match = re.search(r"(evidence-[a-f0-9]+)", prompt)
    return match.group(1) if match else None
