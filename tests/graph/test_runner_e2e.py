import re
import sqlite3
from pathlib import Path
from sqlite3 import Connection

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import EntityRow, PositionRow
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.positions_repo import PositionsRepo
from noesis.graph.runner import build_graph_deps, resume_run, start_run
from noesis.graph.schemas import ConfirmationResult, IngestedDoc
from noesis.tools.llm.router import LLMRole
from noesis.tools.search.fake import FakeSearchAdapter


NOW = "2026-06-26T00:00:00Z"


class DynamicFakeLLM:
    def __init__(self, *, synth_available: bool = True) -> None:
        self.synth_available = synth_available

    def available(self, role: LLMRole) -> bool:
        return role != LLMRole.SYNTH or self.synth_available

    def complete_json(self, role: LLMRole, prompt: str, schema: type) -> object:
        evidence_id = _first_evidence_id(prompt)
        if role == LLMRole.LIGHT:
            return schema.model_validate(
                {
                    "items": [
                        {
                            "title": "Supplier pressure update",
                            "content": "Supplier pressure eased based on cited evidence.",
                            "event_type": "supply_chain",
                            "source": "web",
                            "source_tier": 2,
                            "url": "https://example.com/supplier",
                            "published_at": None,
                            "sentiment": {"dir": "neutral", "conf": 0.7},
                            "evidence_ids": [evidence_id],
                        }
                    ]
                }
            )
        return schema.model_validate(
            {
                "summary": "Evidence suggests supplier pressure is easing.",
                "assumptions": [
                    {
                        "text": "Supplier pressure remains observable in future filings.",
                        "kind": "assumption",
                        "evidence_ids": [evidence_id],
                    }
                ],
            }
        )

    def complete_text(self, role: LLMRole, prompt: str) -> str:
        return "{}"


def _first_evidence_id(prompt: str) -> str:
    match = re.search(r"(evidence-[a-f0-9]+)", prompt)
    if match is None:
        raise AssertionError(f"prompt did not include evidence id: {prompt}")
    return match.group(1)


def make_conn(tmp_path: Path) -> Connection:
    conn = connect(tmp_path / "noesis.db")
    migrate(conn)
    return conn


def seed_position_and_entity(conn: Connection) -> None:
    with with_tx(conn):
        PositionsRepo().insert(
            PositionRow(
                id="position-1",
                user_id="user-1",
                symbol="AAPL",
                market="US",
                name="Apple",
                kind="owned",
                qty=None,
                cost_basis=None,
                created_at=NOW,
                updated_at=NOW,
            ),
            conn=conn,
        )
        EntitiesRepo().upsert(
            EntityRow(
                id="entity-aapl",
                node_type="company",
                name="Apple Inc.",
                aliases_json='["AAPL"]',
                identifiers_json='{"symbol": "AAPL"}',
                market="US",
                created_at=NOW,
                updated_at=NOW,
            ),
            conn=conn,
        )


def make_deps(
    tmp_path: Path,
    conn: Connection,
    *,
    llm: DynamicFakeLLM,
) -> object:
    docs = [
        IngestedDoc(
            source="web",
            source_tier=2,
            title="Supplier update",
            url="https://example.com/supplier",
            text="Supplier pressure eased for Apple.",
        )
    ]
    return build_graph_deps(
        conn=conn,
        checkpoint_conn=sqlite3.connect(
            tmp_path / "checkpoints.db",
            check_same_thread=False,
        ),
        chroma_dir=str(tmp_path / "chroma"),
        search=FakeSearchAdapter(docs),
        llm=llm,
        now=lambda: NOW,
    )


def test_runner_start_resume_happy_path_persists_outputs_and_traces(
    tmp_path: Path,
) -> None:
    conn = make_conn(tmp_path)
    try:
        seed_position_and_entity(conn)
        deps = make_deps(tmp_path, conn, llm=DynamicFakeLLM())

        interrupted = start_run("position-1", deps)
        completed = resume_run(
            interrupted.run_id,
            ConfirmationResult(status="confirmed"),
            deps,
        )

        thesis = deps.repos.theses.get(completed.thesis_id, conn=conn)
        assumptions = deps.repos.assumptions.list_by_thesis(completed.thesis_id, conn=conn)
        intel = deps.repos.intel.list_by_entity("entity-aapl", conn=conn)
        traces = deps.repos.traces.list_by_run(completed.run_id, conn=conn)
    finally:
        conn.close()

    assert interrupted.status == "awaiting_confirmation"
    assert completed.status == "completed"
    assert thesis is not None
    assert assumptions[0].evidence_ids()
    assert intel[0].evidence_ids()
    assert {
        "intake_resolve",
        "ingest",
        "filter",
        "evidence_build",
        "intel_synth",
        "thesis_draft",
        "risk_review",
        "human_confirm",
        "finalize",
    }.issubset({trace.node_name for trace in traces})


def test_runner_completes_when_synth_unavailable_with_degraded_trace(
    tmp_path: Path,
) -> None:
    conn = make_conn(tmp_path)
    try:
        seed_position_and_entity(conn)
        deps = make_deps(tmp_path, conn, llm=DynamicFakeLLM(synth_available=False))

        completed = start_run("position-1", deps)

        traces = deps.repos.traces.list_by_run(completed.run_id, conn=conn)
        thesis = deps.repos.theses.get(f"thesis-{completed.run_id}", conn=conn)
    finally:
        conn.close()

    assert completed.status == "completed"
    assert completed.thesis_id is None
    assert thesis is None
    assert any(trace.status == "degraded" for trace in traces)
