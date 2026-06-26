import sqlite3
from dataclasses import dataclass

from noesis.graph.build_graph import (
    EXPAND_NODE_ORDER,
    SEED_NODE_ORDER,
    build_expand_graph,
    build_seed_graph,
    make_sqlite_checkpointer,
)
from noesis.graph.state import GraphDeps
from noesis.tools.llm.fake import FakeLLMRouter


@dataclass
class EmptyRepos:
    pass


def make_deps() -> GraphDeps:
    return GraphDeps(
        repos=EmptyRepos(),
        search=object(),
        retriever=object(),
        llm=FakeLLMRouter(),
        now=lambda: "2026-06-26T00:00:00Z",
    )


def test_build_seed_graph_compiles_with_expected_node_order() -> None:
    checkpointer = make_sqlite_checkpointer(sqlite3.connect(":memory:"))

    graph = build_seed_graph(make_deps(), checkpointer=checkpointer)

    assert SEED_NODE_ORDER == (
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
    assert set(SEED_NODE_ORDER).issubset(set(graph.nodes))


def test_build_expand_graph_compiles_with_expected_node_order() -> None:
    checkpointer = make_sqlite_checkpointer(sqlite3.connect(":memory:"))

    graph = build_expand_graph(make_deps(), checkpointer=checkpointer)

    assert EXPAND_NODE_ORDER == (
        "intake_resolve",
        "ingest",
        "filter",
        "evidence_build",
        "expand",
        "intel_synth",
        "finalize",
    )
    assert set(EXPAND_NODE_ORDER).issubset(set(graph.nodes))
    assert graph.checkpointer is checkpointer


def test_make_sqlite_checkpointer_sets_up_checkpoint_tables() -> None:
    conn = sqlite3.connect(":memory:")

    checkpointer = make_sqlite_checkpointer(conn)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    graph = build_seed_graph(make_deps(), checkpointer=checkpointer)

    assert {"checkpoints", "writes"}.issubset(tables)
    assert graph.checkpointer is checkpointer
