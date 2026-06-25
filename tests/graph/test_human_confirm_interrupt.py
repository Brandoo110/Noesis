from dataclasses import dataclass, field

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from noesis.db.models import ApprovalRow
from noesis.graph.nodes.human_confirm import human_confirm
from noesis.graph.schemas import ThesisAssumptionDraft, ThesisDraft
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate
from noesis.tools.llm.fake import FakeLLMRouter


NOW = "2026-06-26T00:00:00Z"


@dataclass
class FakeApprovalsRepo:
    inserted: list[ApprovalRow] = field(default_factory=list)

    def insert(self, row: ApprovalRow) -> None:
        self.inserted.append(row)

    def get_by_object(self, object_type: str, object_id: str) -> ApprovalRow | None:
        for row in self.inserted:
            if row.object_type == object_type and row.object_id == object_id:
                return row
        return None


@dataclass
class FakeRunsRepo:
    statuses: list[tuple[str, str, str | None]] = field(default_factory=list)

    def set_status(self, id: str, status: str, ended_at: str | None) -> None:
        self.statuses.append((id, status, ended_at))


@dataclass
class FakeRepos:
    approvals: FakeApprovalsRepo
    runs: FakeRunsRepo


def make_deps(repos: FakeRepos) -> GraphDeps:
    return GraphDeps(
        repos=repos,
        search=object(),
        retriever=object(),
        llm=FakeLLMRouter(),
        now=lambda: NOW,
    )


def make_thesis() -> ThesisDraft:
    return ThesisDraft(
        summary="Evidence-backed thesis.",
        assumptions=[
            ThesisAssumptionDraft(
                text="Supplier pressure remains observable.",
                kind="assumption",
                evidence_ids=["evidence-1"],
            )
        ],
    )


def test_human_confirm_writes_pending_approval_and_interrupts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []

    def fake_interrupt(payload: dict[str, str]) -> dict[str, str]:
        calls.append(payload)
        return {"status": "confirmed"}

    monkeypatch.setattr("noesis.graph.nodes.human_confirm.interrupt", fake_interrupt)
    repos = FakeRepos(approvals=FakeApprovalsRepo(), runs=FakeRunsRepo())
    state: ResearchState = {
        "run_id": "run-1",
        "thesis_draft": make_thesis(),
        "degraded": [],
    }

    update = human_confirm(state, make_deps(repos))

    assert repos.approvals.inserted[0].status == "pending"
    assert repos.runs.statuses == [("run-1", "awaiting_confirmation", None)]
    assert calls[0]["approval_id"] == "approval-run-1"
    assert update["confirmation"].status == "confirmed"


def test_human_confirm_skips_when_thesis_is_missing() -> None:
    repos = FakeRepos(approvals=FakeApprovalsRepo(), runs=FakeRunsRepo())
    state: ResearchState = {"run_id": "run-1", "thesis_draft": None, "degraded": []}

    update = human_confirm(state, make_deps(repos))

    assert repos.approvals.inserted == []
    assert update["confirmation"].status == "confirmed"
    assert update["degraded"][0].fallback_used == "skip_confirmation"


def test_human_confirm_interrupts_and_resumes_in_minimal_graph() -> None:
    repos = FakeRepos(approvals=FakeApprovalsRepo(), runs=FakeRunsRepo())
    deps = make_deps(repos)
    reached_finalize: list[str] = []

    def confirm_node(state: ResearchState) -> ResearchStateUpdate:
        return human_confirm(state, deps)

    def finalize_node(state: ResearchState) -> ResearchStateUpdate:
        reached_finalize.append("finalize")
        return {}

    graph_builder = StateGraph(ResearchState)
    graph_builder.add_node("human_confirm", confirm_node)
    graph_builder.add_node("finalize", finalize_node)
    graph_builder.set_entry_point("human_confirm")
    graph_builder.add_edge("human_confirm", "finalize")
    graph_builder.add_edge("finalize", END)
    graph = graph_builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "thread-run-1"}}
    state: ResearchState = {
        "run_id": "run-1",
        "thesis_draft": make_thesis(),
        "degraded": [],
    }

    interrupted = graph.invoke(state, config)
    resumed = graph.invoke(Command(resume={"status": "confirmed"}), config)

    assert "__interrupt__" in interrupted
    assert reached_finalize == ["finalize"]
    assert resumed["confirmation"].status == "confirmed"
