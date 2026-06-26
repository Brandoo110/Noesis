import sqlite3
from collections.abc import Callable

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from noesis.graph.schemas import (
    ConfirmationResult,
    DegradeNote,
    EvidenceRecord,
    GraphEdgeDraft,
    IngestedDoc,
    IntelItemDraft,
    PositionInput,
    ResolvedEntity,
    RiskFinding,
    SentimentTag,
    ThesisAssumptionDraft,
    ThesisDraft,
)
from noesis.graph.nodes.evidence_build import evidence_build
from noesis.graph.nodes.expand import expand
from noesis.graph.nodes.filter import filter as filter_node
from noesis.graph.nodes.finalize import finalize
from noesis.graph.nodes.human_confirm import human_confirm
from noesis.graph.nodes.ingest import ingest
from noesis.graph.nodes.intake_resolve import intake_resolve
from noesis.graph.nodes.intel_synth import intel_synth
from noesis.graph.nodes.risk_review import risk_review
from noesis.graph.nodes.thesis_draft import thesis_draft
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate

SEED_NODE_ORDER = (
    "intake_resolve",
    "ingest",
    "filter",
    "evidence_build",
    "expand",
    "intel_synth",
    "thesis_draft",
    "risk_review",
    "human_confirm",
    "finalize",
)

EXPAND_NODE_ORDER = (
    "intake_resolve",
    "ingest",
    "filter",
    "evidence_build",
    "expand",
    "intel_synth",
    "finalize",
)

NodeFn = Callable[[ResearchState, GraphDeps], ResearchStateUpdate]
BoundNodeFn = Callable[[ResearchState], ResearchStateUpdate]
NodeWrapper = Callable[[str, NodeFn, GraphDeps], BoundNodeFn]

NODE_FUNCTIONS: dict[str, NodeFn] = {
    "intake_resolve": intake_resolve,
    "ingest": ingest,
    "filter": filter_node,
    "evidence_build": evidence_build,
    "expand": expand,
    "intel_synth": intel_synth,
    "thesis_draft": thesis_draft,
    "risk_review": risk_review,
    "human_confirm": human_confirm,
    "finalize": finalize,
}


CHECKPOINT_ALLOWED_TYPES = (
    ConfirmationResult,
    DegradeNote,
    EvidenceRecord,
    GraphEdgeDraft,
    IngestedDoc,
    IntelItemDraft,
    PositionInput,
    ResolvedEntity,
    RiskFinding,
    SentimentTag,
    ThesisAssumptionDraft,
    ThesisDraft,
)


def make_sqlite_checkpointer(conn: sqlite3.Connection) -> SqliteSaver:
    checkpointer = SqliteSaver(
        conn,
        serde=JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_ALLOWED_TYPES),
    )
    checkpointer.setup()
    return checkpointer


def build_seed_graph(
    deps: GraphDeps,
    *,
    checkpointer: SqliteSaver,
    node_wrapper: NodeWrapper | None = None,
) -> CompiledStateGraph:
    graph = StateGraph(ResearchState)
    for node_name in SEED_NODE_ORDER:
        node_fn = NODE_FUNCTIONS[node_name]
        bound = node_wrapper(node_name, node_fn, deps) if node_wrapper else _bind_deps(node_fn, deps)
        graph.add_node(node_name, bound)
    graph.set_entry_point(SEED_NODE_ORDER[0])
    for from_node, to_node in zip(SEED_NODE_ORDER, SEED_NODE_ORDER[1:]):
        graph.add_edge(from_node, to_node)
    graph.add_edge(SEED_NODE_ORDER[-1], END)
    return graph.compile(checkpointer=checkpointer)


def build_expand_graph(
    deps: GraphDeps,
    *,
    checkpointer: SqliteSaver,
    node_wrapper: NodeWrapper | None = None,
) -> CompiledStateGraph:
    graph = StateGraph(ResearchState)
    for node_name in EXPAND_NODE_ORDER:
        node_fn = NODE_FUNCTIONS[node_name]
        bound = node_wrapper(node_name, node_fn, deps) if node_wrapper else _bind_deps(node_fn, deps)
        graph.add_node(node_name, bound)
    graph.set_entry_point(EXPAND_NODE_ORDER[0])
    for from_node, to_node in zip(EXPAND_NODE_ORDER, EXPAND_NODE_ORDER[1:]):
        graph.add_edge(from_node, to_node)
    graph.add_edge(EXPAND_NODE_ORDER[-1], END)
    return graph.compile(checkpointer=checkpointer)


def _bind_deps(node_fn: NodeFn, deps: GraphDeps) -> BoundNodeFn:
    def run_node(state: ResearchState) -> ResearchStateUpdate:
        return node_fn(state, deps)

    return run_node
