from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Literal, TypedDict

from noesis.graph.schemas import (
    ConfirmationResult,
    DegradeNote,
    EvidenceRecord,
    IngestedDoc,
    IntelItemDraft,
    PositionInput,
    ResolvedEntity,
    RiskFinding,
    ThesisDraft,
)

if TYPE_CHECKING:
    from noesis.db.repos.approvals_repo import ApprovalsRepo
    from noesis.db.repos.entities_repo import EntitiesRepo
    from noesis.db.repos.evidences_repo import EvidencesRepo
    from noesis.db.repos.intel_items_repo import IntelItemsRepo
    from noesis.db.repos.node_traces_repo import NodeTracesRepo
    from noesis.db.repos.positions_repo import PositionsRepo
    from noesis.db.repos.run_registry_repo import RunRegistryRepo
    from noesis.db.repos.theses_repo import ThesesRepo
    from noesis.db.repos.thesis_assumptions_repo import ThesisAssumptionsRepo
    from noesis.tools.llm.router import LLMRouter
    from noesis.tools.retrieval.store import EvidenceRetriever
    from noesis.tools.search.base import SearchAdapter


class ResearchState(TypedDict, total=False):
    run_id: str
    position_id: str | None
    entity_id: str | None
    node_kind: Literal["seed", "expand"]
    raw_input: PositionInput | None
    resolved_entity: ResolvedEntity | None
    ingested_docs: list[IngestedDoc]
    filtered_docs: list[IngestedDoc]
    evidences: list[EvidenceRecord]
    intel_items: list[IntelItemDraft]
    thesis_draft: ThesisDraft | None
    risk_findings: list[RiskFinding]
    confirmation: ConfirmationResult | None
    degraded: list[DegradeNote]


ResearchStateUpdate = dict[str, Any]


@dataclass
class RepoBundle:
    positions: PositionsRepo
    entities: EntitiesRepo
    runs: RunRegistryRepo
    traces: NodeTracesRepo
    evidences: EvidencesRepo
    intel: IntelItemsRepo
    theses: ThesesRepo
    assumptions: ThesisAssumptionsRepo
    approvals: ApprovalsRepo


@dataclass
class GraphDeps:
    repos: RepoBundle
    search: SearchAdapter
    retriever: EvidenceRetriever
    llm: LLMRouter
    now: Callable[[], str]
