from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import ApprovalRow, RunRow
from noesis.db.repos.approvals_repo import ApprovalsRepo
from noesis.db.repos.evidences_repo import EvidencesRepo
from noesis.db.repos.intel_items_repo import IntelItemsRepo
from noesis.db.repos.run_registry_repo import RunRegistryRepo
from noesis.db.repos.theses_repo import ThesesRepo
from noesis.db.repos.thesis_assumptions_repo import ThesisAssumptionsRepo
from noesis.graph.nodes.finalize import finalize
from noesis.graph.schemas import (
    ConfirmationResult,
    EvidenceRecord,
    IntelItemDraft,
    SentimentTag,
    ThesisAssumptionDraft,
    ThesisDraft,
)
from noesis.graph.state import GraphDeps, ResearchState
from noesis.tools.llm.fake import FakeLLMRouter


NOW = "2026-06-26T00:00:00Z"


@dataclass
class RepoSession:
    conn: Connection
    evidences: EvidencesRepo
    intel: IntelItemsRepo
    theses: ThesesRepo
    assumptions: ThesisAssumptionsRepo
    approvals: ApprovalsRepo
    runs: RunRegistryRepo


def make_repo_session(conn: Connection) -> RepoSession:
    return RepoSession(
        conn=conn,
        evidences=EvidencesRepo(),
        intel=IntelItemsRepo(),
        theses=ThesesRepo(),
        assumptions=ThesisAssumptionsRepo(),
        approvals=ApprovalsRepo(),
        runs=RunRegistryRepo(),
    )


def make_deps(repos: RepoSession) -> GraphDeps:
    return GraphDeps(
        repos=repos,
        search=object(),
        retriever=object(),
        llm=FakeLLMRouter(),
        now=lambda: NOW,
    )


def make_db(tmp_path: Path) -> Connection:
    conn = connect(tmp_path / "noesis.db")
    migrate(conn)
    with with_tx(conn):
        RunRegistryRepo().insert(
            RunRow(
                id="run-1",
                position_id="position-1",
                entity_id="entity-1",
                node_kind="seed",
                status="awaiting_confirmation",
                started_at=NOW,
                ended_at=None,
                created_at=NOW,
            ),
            conn=conn,
        )
        ApprovalsRepo().insert(
            ApprovalRow(
                id="approval-run-1",
                run_id="run-1",
                object_type="thesis",
                object_id="thesis-run-1",
                status="pending",
                payload_json=None,
                created_at=NOW,
                updated_at=NOW,
            ),
            conn=conn,
        )
    return conn


def make_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        id="evidence-1",
        run_id="run-1",
        source="web",
        source_tier=2,
        url="https://example.com/evidence-1",
        title="Evidence",
        snippet="Supplier pressure eased.",
        captured_at=NOW,
    )


def make_intel() -> IntelItemDraft:
    return IntelItemDraft(
        title="Supplier update",
        content="Supplier pressure eased based on cited evidence.",
        event_type="supply_chain",
        source="web",
        source_tier=2,
        url="https://example.com/evidence-1",
        published_at=None,
        sentiment=SentimentTag(dir="neutral", conf=0.7),
        evidence_ids=["evidence-1"],
    )


def make_thesis(summary: str = "Evidence-backed thesis.") -> ThesisDraft:
    return ThesisDraft(
        summary=summary,
        assumptions=[
            ThesisAssumptionDraft(
                text="Supplier pressure remains observable.",
                kind="assumption",
                evidence_ids=["evidence-1"],
            )
        ],
    )


def make_state(confirmation: ConfirmationResult, thesis: ThesisDraft | None) -> ResearchState:
    return {
        "run_id": "run-1",
        "position_id": "position-1",
        "entity_id": "entity-1",
        "evidences": [make_evidence()],
        "intel_items": [make_intel()],
        "thesis_draft": thesis,
        "confirmation": confirmation,
        "degraded": [],
    }


def test_finalize_persists_confirmed_outputs(tmp_path: Path) -> None:
    conn = make_db(tmp_path)
    try:
        repos = make_repo_session(conn)
        state = make_state(ConfirmationResult(status="confirmed"), make_thesis())

        update = finalize(state, make_deps(repos))

        thesis = repos.theses.get("thesis-run-1", conn=conn)
        assumptions = repos.assumptions.list_by_thesis("thesis-run-1", conn=conn)
        approval = repos.approvals.get_by_object("thesis", "thesis-run-1", conn=conn)
        run = repos.runs.get("run-1", conn=conn)
        intel = repos.intel.list_by_entity("entity-1", conn=conn)
        evidences = repos.evidences.list_by_run("run-1", conn=conn)
    finally:
        conn.close()

    assert update["thesis_id"] == "thesis-run-1"
    assert thesis is not None and thesis.status == "confirmed"
    assert assumptions[0].evidence_ids() == ["evidence-1"]
    assert approval is not None and approval.status == "confirmed"
    assert run is not None and run.status == "completed"
    assert intel[0].evidence_ids() == ["evidence-1"]
    assert evidences[0].id == "evidence-1"


def test_finalize_uses_edited_confirmation_payload(tmp_path: Path) -> None:
    conn = make_db(tmp_path)
    edited_assumption = ThesisAssumptionDraft(
        text="Edited assumption.",
        kind="assumption",
        evidence_ids=["evidence-1"],
    )
    try:
        repos = make_repo_session(conn)
        state = make_state(
            ConfirmationResult(
                status="edited",
                edited_summary="Edited summary.",
                edited_assumptions=[edited_assumption],
            ),
            make_thesis(),
        )

        finalize(state, make_deps(repos))

        thesis = repos.theses.get("thesis-run-1", conn=conn)
        assumptions = repos.assumptions.list_by_thesis("thesis-run-1", conn=conn)
    finally:
        conn.close()

    assert thesis is not None and thesis.summary == "Edited summary."
    assert assumptions[0].text == "Edited assumption."


def test_finalize_completes_without_thesis_when_upstream_degraded(tmp_path: Path) -> None:
    conn = make_db(tmp_path)
    try:
        repos = make_repo_session(conn)
        state = make_state(ConfirmationResult(status="confirmed"), None)

        update = finalize(state, make_deps(repos))

        run = repos.runs.get("run-1", conn=conn)
    finally:
        conn.close()

    assert update["thesis_id"] is None
    assert run is not None and run.status == "completed"
    assert update["degraded"][0].fallback_used == "complete_without_thesis"
