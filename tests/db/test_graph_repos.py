from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import GraphEdgeRow, HoldingRelevanceRow, NodeExpansionRow
from noesis.db.repos.graph_edges_repo import GraphEdgesRepo
from noesis.db.repos.holding_relevances_repo import HoldingRelevancesRepo
from noesis.db.repos.node_expansions_repo import NodeExpansionsRepo

NOW = "2026-06-26T00:00:00Z"


def make_edge(
    id: str = "edge-1",
    *,
    from_entity_id: str = "entity-aapl",
    to_entity_id: str = "entity-tsmc",
    relation: str = "supplier",
    basis: str = "source_backed",
    confidence: float = 0.8,
) -> GraphEdgeRow:
    return GraphEdgeRow(
        id=id,
        from_entity_id=from_entity_id,
        to_entity_id=to_entity_id,
        relation=relation,
        basis=basis,
        confidence=confidence,
        evidence_ids_json='["evidence-1"]',
        run_id="run-1",
        rationale="TSMC supplies chips to Apple.",
        created_at=NOW,
    )


def make_expansion(
    entity_id: str = "entity-aapl",
    *,
    researched: int = 0,
) -> NodeExpansionRow:
    return NodeExpansionRow(
        entity_id=entity_id,
        researched=researched,
        researched_at=None,
        cached_run_id=None,
        created_at=NOW,
        updated_at=NOW,
    )


def make_relevance(id: str = "relevance-1") -> HoldingRelevanceRow:
    return HoldingRelevanceRow(
        id=id,
        entity_id="entity-tsmc",
        position_id="position-1",
        path_json='["entity-tsmc", "entity-aapl"]',
        created_at=NOW,
    )


def test_graph_edges_repo_insert_list_delete_and_empty_results(db: Connection) -> None:
    repo = GraphEdgesRepo()
    first = make_edge("edge-1")
    second = make_edge("edge-2", from_entity_id="entity-aapl", to_entity_id="entity-foxconn")

    with with_tx(db):
        repo.insert_many([first, second], conn=db)

    assert repo.list_from("entity-aapl", conn=db) == [first, second]
    assert repo.list_to("entity-tsmc", conn=db) == [first]
    assert repo.list_from("missing", conn=db) == []
    assert repo.list_to("missing", conn=db) == []

    with with_tx(db):
        repo.delete("edge-1", conn=db)

    assert repo.list_from("entity-aapl", conn=db) == [second]


def test_graph_edges_repo_does_not_commit_implicitly(db: Connection) -> None:
    repo = GraphEdgesRepo()

    repo.insert_many([make_edge("edge-rollback")], conn=db)
    db.rollback()

    assert repo.list_from("entity-aapl", conn=db) == []


def test_graph_edges_repo_dedupes_source_backed_before_confidence(
    db: Connection,
) -> None:
    repo = GraphEdgesRepo()
    inferred = make_edge("edge-inferred", basis="inferred", confidence=0.5)
    source_backed = make_edge("edge-source-backed", basis="source_backed", confidence=0.4)

    with with_tx(db):
        repo.insert_many([inferred, source_backed], conn=db)

    assert repo.list_from("entity-aapl", conn=db) == [source_backed]
    assert repo.list_to("entity-tsmc", conn=db) == [source_backed]


def test_graph_edges_repo_dedupes_inferred_edges_by_confidence(
    db: Connection,
) -> None:
    repo = GraphEdgesRepo()
    lower = make_edge("edge-low", basis="inferred", confidence=0.5)
    higher = make_edge("edge-high", basis="inferred", confidence=0.7)

    with with_tx(db):
        repo.insert_many([lower, higher], conn=db)

    assert repo.list_from("entity-aapl", conn=db) == [higher]


def test_graph_edges_repo_keeps_distinct_relations(db: Connection) -> None:
    repo = GraphEdgesRepo()
    supplier = make_edge("edge-1", relation="supplier")
    competitor = make_edge("edge-2", relation="competitor")

    with with_tx(db):
        repo.insert_many([supplier, competitor], conn=db)

    assert repo.list_from("entity-aapl", conn=db) == [supplier, competitor]


def test_node_expansions_repo_upsert_mark_researched_and_empty_result(
    db: Connection,
) -> None:
    repo = NodeExpansionsRepo()

    assert repo.get("missing", conn=db) is None

    with with_tx(db):
        repo.upsert(make_expansion(), conn=db)

    assert repo.get("entity-aapl", conn=db) == make_expansion()

    with with_tx(db):
        repo.mark_researched("entity-aapl", "run-1", NOW, conn=db)
        repo.mark_researched("entity-aapl", "run-1", NOW, conn=db)

    row = repo.get("entity-aapl", conn=db)
    assert row == NodeExpansionRow(
        entity_id="entity-aapl",
        researched=1,
        researched_at=NOW,
        cached_run_id="run-1",
        created_at=NOW,
        updated_at=NOW,
    )


def test_node_expansions_repo_mark_researched_creates_missing_row(
    db: Connection,
) -> None:
    repo = NodeExpansionsRepo()

    with with_tx(db):
        repo.mark_researched("entity-new", "run-2", NOW, conn=db)

    row = repo.get("entity-new", conn=db)
    assert row is not None
    assert row.researched == 1
    assert row.cached_run_id == "run-2"


def test_holding_relevances_repo_upsert_list_by_entity_and_empty_result(
    db: Connection,
) -> None:
    repo = HoldingRelevancesRepo()
    first = make_relevance("relevance-1")
    second = HoldingRelevanceRow(
        id="relevance-2",
        entity_id="entity-tsmc",
        position_id="position-2",
        path_json='["entity-tsmc", "entity-msft"]',
        created_at=NOW,
    )

    assert repo.list_by_entity("missing", conn=db) == []

    with with_tx(db):
        repo.upsert(first, conn=db)
        repo.upsert(second, conn=db)

    assert repo.list_by_entity("entity-tsmc", conn=db) == [first, second]

    updated = first.model_copy(update={"path_json": '["entity-tsmc", "entity-aapl", "entity-seed"]'})
    with with_tx(db):
        repo.upsert(updated, conn=db)

    assert repo.list_by_entity("entity-tsmc", conn=db)[0].path() == [
        "entity-tsmc",
        "entity-aapl",
        "entity-seed",
    ]
