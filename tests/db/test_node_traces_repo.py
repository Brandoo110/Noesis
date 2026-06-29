from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import NodeTraceRow
from noesis.db.repos.node_traces_repo import NodeTracesRepo


NOW = "2026-06-26T00:00:00Z"


def make_trace(id: str, run_id: str = "run-1") -> NodeTraceRow:
    return NodeTraceRow(
        id=id,
        run_id=run_id,
        node_name="ingest",
        entity_id="entity-1",
        inputs_ref="input",
        outputs_ref="output",
        status="success",
        reason=None,
        fallback_used=None,
        model_id=None,
        evidence_ids_json='["evidence-1"]',
        started_at=NOW,
        ended_at=NOW,
        created_at=NOW,
    )


def test_node_traces_repo_insert_and_list_by_run(db: Connection) -> None:
    repo = NodeTracesRepo()
    row = make_trace("trace-1")

    with with_tx(db):
        repo.insert(row, conn=db)

    assert repo.list_by_run("run-1", conn=db) == [row]


def test_node_traces_repo_empty_result(db: Connection) -> None:
    assert NodeTracesRepo().list_by_run("missing", conn=db) == []


def test_node_traces_repo_lists_by_run_ids(db: Connection) -> None:
    repo = NodeTracesRepo()
    first = make_trace("trace-1", "run-1")
    second = make_trace("trace-2", "run-2")
    skipped = make_trace("trace-3", "run-3")

    with with_tx(db):
        repo.insert(first, conn=db)
        repo.insert(second, conn=db)
        repo.insert(skipped, conn=db)

    assert repo.list_by_run_ids(["run-1", "run-2"], conn=db) == [first, second]
    assert repo.list_by_run_ids([], conn=db) == []


def test_node_traces_repo_reads_started_trace_without_ended_at(
    db: Connection,
) -> None:
    db.execute(
        """
        INSERT INTO node_traces(
          id, run_id, node_name, entity_id, inputs_ref, outputs_ref, status,
          reason, fallback_used, model_id, evidence_ids_json, started_at,
          ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "trace-started",
            "run-1",
            "ingest",
            "entity-1",
            None,
            None,
            "started",
            None,
            None,
            None,
            None,
            NOW,
            None,
            NOW,
        ),
    )

    trace = NodeTracesRepo().list_by_run("run-1", conn=db)[0]

    assert trace.status == "started"
    assert trace.ended_at is None
