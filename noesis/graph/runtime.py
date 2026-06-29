from dataclasses import dataclass, field
from sqlite3 import Connection

from noesis.db.models import (
    ApprovalRow,
    EntityRow,
    EvidenceRow,
    GraphEdgeRow,
    HoldingRelevanceRow,
    IntelItemRow,
    NodeExpansionRow,
    NodeTraceRow,
    PositionRow,
    RunRow,
    ThesisAssumptionRow,
    ThesisRow,
)
from noesis.db.repos.approvals_repo import ApprovalsRepo
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.evidences_repo import EvidencesRepo
from noesis.db.repos.graph_edges_repo import GraphEdgesRepo
from noesis.db.repos.holding_relevances_repo import HoldingRelevancesRepo
from noesis.db.repos.intel_items_repo import IntelItemsRepo
from noesis.db.repos.node_expansions_repo import NodeExpansionsRepo
from noesis.db.repos.node_traces_repo import NodeTracesRepo
from noesis.db.repos.positions_repo import PositionsRepo
from noesis.db.repos.run_registry_repo import RunRegistryRepo
from noesis.db.repos.theses_repo import ThesesRepo
from noesis.db.repos.thesis_assumptions_repo import ThesisAssumptionsRepo


@dataclass
class PositionsRuntime:
    conn: Connection
    repo: PositionsRepo = field(default_factory=PositionsRepo)

    def insert(self, row: PositionRow, *, conn: Connection | None = None) -> None:
        self.repo.insert(row, conn=conn or self.conn)

    def get(self, id: str, *, conn: Connection | None = None) -> PositionRow | None:
        return self.repo.get(id, conn=conn or self.conn)

    def list_by_identity(
        self,
        user_id: str,
        symbol: str,
        market: str,
        kind: str,
        *,
        conn: Connection | None = None,
    ) -> list[PositionRow]:
        return self.repo.list_by_identity(
            user_id,
            symbol,
            market,
            kind,
            conn=conn or self.conn,
        )

    def list_by_user(
        self, user_id: str, *, conn: Connection | None = None
    ) -> list[PositionRow]:
        return self.repo.list_by_user(user_id, conn=conn or self.conn)


@dataclass
class EntitiesRuntime:
    conn: Connection
    repo: EntitiesRepo = field(default_factory=EntitiesRepo)

    def find_by_symbol(
        self, market: str | None, symbol: str, *, conn: Connection | None = None
    ) -> EntityRow | None:
        return self.repo.find_by_symbol(market, symbol, conn=conn or self.conn)

    def upsert(self, row: EntityRow, *, conn: Connection | None = None) -> EntityRow:
        return self.repo.upsert(row, conn=conn or self.conn)

    def get(self, id: str, *, conn: Connection | None = None) -> EntityRow | None:
        return self.repo.get(id, conn=conn or self.conn)


@dataclass
class RunsRuntime:
    conn: Connection
    repo: RunRegistryRepo = field(default_factory=RunRegistryRepo)

    def insert(self, row: RunRow, *, conn: Connection | None = None) -> None:
        self.repo.insert(row, conn=conn or self.conn)

    def get(self, id: str, *, conn: Connection | None = None) -> RunRow | None:
        return self.repo.get(id, conn=conn or self.conn)

    def get_seed_entity_id(
        self, position_id: str, *, conn: Connection | None = None
    ) -> str | None:
        return self.repo.get_seed_entity_id(position_id, conn=conn or self.conn)

    def latest_seed_for_position(
        self, position_id: str, *, conn: Connection | None = None
    ) -> RunRow | None:
        return self.repo.latest_seed_for_position(position_id, conn=conn or self.conn)

    def latest_seed_for_positions(
        self, position_ids: list[str], *, conn: Connection | None = None
    ) -> list[RunRow]:
        return self.repo.latest_seed_for_positions(position_ids, conn=conn or self.conn)

    def set_entity(
        self, id: str, entity_id: str, *, conn: Connection | None = None
    ) -> None:
        self.repo.set_entity(id, entity_id, conn=conn or self.conn)

    def set_status(
        self,
        id: str,
        status: str,
        ended_at: str | None,
        *,
        conn: Connection | None = None,
    ) -> None:
        self.repo.set_status(id, status, ended_at, conn=conn or self.conn)


@dataclass
class TracesRuntime:
    conn: Connection
    repo: NodeTracesRepo = field(default_factory=NodeTracesRepo)

    def insert(self, row: NodeTraceRow, *, conn: Connection | None = None) -> None:
        self.repo.insert(row, conn=conn or self.conn)

    def list_by_run(
        self, run_id: str, *, conn: Connection | None = None
    ) -> list[NodeTraceRow]:
        return self.repo.list_by_run(run_id, conn=conn or self.conn)

    def list_by_run_ids(
        self, run_ids: list[str], *, conn: Connection | None = None
    ) -> list[NodeTraceRow]:
        return self.repo.list_by_run_ids(run_ids, conn=conn or self.conn)


@dataclass
class EvidencesRuntime:
    conn: Connection
    repo: EvidencesRepo = field(default_factory=EvidencesRepo)

    def insert_many(
        self, rows: list[EvidenceRow], *, conn: Connection | None = None
    ) -> None:
        self.repo.insert_many(rows, conn=conn or self.conn)

    def get(self, id: str, *, conn: Connection | None = None) -> EvidenceRow | None:
        return self.repo.get(id, conn=conn or self.conn)

    def list_by_run(
        self, run_id: str, *, conn: Connection | None = None
    ) -> list[EvidenceRow]:
        return self.repo.list_by_run(run_id, conn=conn or self.conn)


@dataclass
class IntelRuntime:
    conn: Connection
    repo: IntelItemsRepo = field(default_factory=IntelItemsRepo)

    def insert_many(
        self, rows: list[IntelItemRow], *, conn: Connection | None = None
    ) -> None:
        self.repo.insert_many(rows, conn=conn or self.conn)

    def list_by_entity(
        self, entity_id: str, *, conn: Connection | None = None
    ) -> list[IntelItemRow]:
        return self.repo.list_by_entity(entity_id, conn=conn or self.conn)


@dataclass
class ThesesRuntime:
    conn: Connection
    repo: ThesesRepo = field(default_factory=ThesesRepo)

    def insert(self, row: ThesisRow, *, conn: Connection | None = None) -> None:
        self.repo.insert(row, conn=conn or self.conn)

    def get(self, id: str, *, conn: Connection | None = None) -> ThesisRow | None:
        return self.repo.get(id, conn=conn or self.conn)

    def latest_for_position(
        self, position_id: str, *, conn: Connection | None = None
    ) -> ThesisRow | None:
        return self.repo.latest_for_position(position_id, conn=conn or self.conn)

    def list_by_run_ids(
        self, run_ids: list[str], *, conn: Connection | None = None
    ) -> list[ThesisRow]:
        return self.repo.list_by_run_ids(run_ids, conn=conn or self.conn)


@dataclass
class AssumptionsRuntime:
    conn: Connection
    repo: ThesisAssumptionsRepo = field(default_factory=ThesisAssumptionsRepo)

    def insert_many(
        self, rows: list[ThesisAssumptionRow], *, conn: Connection | None = None
    ) -> None:
        self.repo.insert_many(rows, conn=conn or self.conn)

    def list_by_thesis(
        self, thesis_id: str, *, conn: Connection | None = None
    ) -> list[ThesisAssumptionRow]:
        return self.repo.list_by_thesis(thesis_id, conn=conn or self.conn)


@dataclass
class ApprovalsRuntime:
    conn: Connection
    repo: ApprovalsRepo = field(default_factory=ApprovalsRepo)

    def insert(self, row: ApprovalRow, *, conn: Connection | None = None) -> None:
        self.repo.insert(row, conn=conn or self.conn)

    def get_by_object(
        self, object_type: str, object_id: str, *, conn: Connection | None = None
    ) -> ApprovalRow | None:
        return self.repo.get_by_object(object_type, object_id, conn=conn or self.conn)

    def set_status(
        self, id: str, status: str, updated_at: str, *, conn: Connection | None = None
    ) -> None:
        self.repo.set_status(id, status, updated_at, conn=conn or self.conn)


@dataclass
class GraphEdgesRuntime:
    conn: Connection
    repo: GraphEdgesRepo = field(default_factory=GraphEdgesRepo)

    def insert_many(
        self, rows: list[GraphEdgeRow], *, conn: Connection | None = None
    ) -> None:
        self.repo.insert_many(rows, conn=conn or self.conn)

    def list_from(
        self, entity_id: str, *, conn: Connection | None = None
    ) -> list[GraphEdgeRow]:
        return self.repo.list_from(entity_id, conn=conn or self.conn)

    def list_to(
        self, entity_id: str, *, conn: Connection | None = None
    ) -> list[GraphEdgeRow]:
        return self.repo.list_to(entity_id, conn=conn or self.conn)

    def delete(self, id: str, *, conn: Connection | None = None) -> None:
        self.repo.delete(id, conn=conn or self.conn)


@dataclass
class NodeExpansionsRuntime:
    conn: Connection
    repo: NodeExpansionsRepo = field(default_factory=NodeExpansionsRepo)

    def get(
        self, entity_id: str, *, conn: Connection | None = None
    ) -> NodeExpansionRow | None:
        return self.repo.get(entity_id, conn=conn or self.conn)

    def upsert(self, row: NodeExpansionRow, *, conn: Connection | None = None) -> None:
        self.repo.upsert(row, conn=conn or self.conn)

    def mark_researched(
        self,
        entity_id: str,
        run_id: str,
        at: str,
        *,
        conn: Connection | None = None,
    ) -> None:
        self.repo.mark_researched(entity_id, run_id, at, conn=conn or self.conn)


@dataclass
class HoldingRelevancesRuntime:
    conn: Connection
    repo: HoldingRelevancesRepo = field(default_factory=HoldingRelevancesRepo)

    def upsert(
        self, row: HoldingRelevanceRow, *, conn: Connection | None = None
    ) -> None:
        self.repo.upsert(row, conn=conn or self.conn)

    def list_by_entity(
        self, entity_id: str, *, conn: Connection | None = None
    ) -> list[HoldingRelevanceRow]:
        return self.repo.list_by_entity(entity_id, conn=conn or self.conn)


@dataclass
class RepoRuntime:
    conn: Connection
    positions: PositionsRuntime = field(init=False)
    entities: EntitiesRuntime = field(init=False)
    runs: RunsRuntime = field(init=False)
    traces: TracesRuntime = field(init=False)
    evidences: EvidencesRuntime = field(init=False)
    intel: IntelRuntime = field(init=False)
    theses: ThesesRuntime = field(init=False)
    assumptions: AssumptionsRuntime = field(init=False)
    approvals: ApprovalsRuntime = field(init=False)
    graph_edges: GraphEdgesRuntime = field(init=False)
    node_expansions: NodeExpansionsRuntime = field(init=False)
    holding_relevances: HoldingRelevancesRuntime = field(init=False)

    def __post_init__(self) -> None:
        self.positions = PositionsRuntime(self.conn)
        self.entities = EntitiesRuntime(self.conn)
        self.runs = RunsRuntime(self.conn)
        self.traces = TracesRuntime(self.conn)
        self.evidences = EvidencesRuntime(self.conn)
        self.intel = IntelRuntime(self.conn)
        self.theses = ThesesRuntime(self.conn)
        self.assumptions = AssumptionsRuntime(self.conn)
        self.approvals = ApprovalsRuntime(self.conn)
        self.graph_edges = GraphEdgesRuntime(self.conn)
        self.node_expansions = NodeExpansionsRuntime(self.conn)
        self.holding_relevances = HoldingRelevancesRuntime(self.conn)
