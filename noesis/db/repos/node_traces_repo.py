import sqlite3

from noesis.db.models import NodeTraceRow
from noesis.db.repos._mapping import rows_to_models


class NodeTracesRepo:
    def insert(self, row: NodeTraceRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO node_traces(
              id, run_id, node_name, entity_id, inputs_ref, outputs_ref, status,
              reason, fallback_used, model_id, evidence_ids_json, started_at,
              ended_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.id,
                row.run_id,
                row.node_name,
                row.entity_id,
                row.inputs_ref,
                row.outputs_ref,
                row.status,
                row.reason,
                row.fallback_used,
                row.model_id,
                row.evidence_ids_json,
                row.started_at,
                row.ended_at,
                row.created_at,
            ),
        )

    def list_by_run(self, run_id: str, *, conn: sqlite3.Connection) -> list[NodeTraceRow]:
        rows = conn.execute(
            "SELECT * FROM node_traces WHERE run_id = ? ORDER BY started_at, id",
            (run_id,),
        ).fetchall()
        return rows_to_models(rows, NodeTraceRow)

    def list_by_run_ids(
        self, run_ids: list[str], *, conn: sqlite3.Connection
    ) -> list[NodeTraceRow]:
        if not run_ids:
            return []
        placeholders = ", ".join("?" for _ in run_ids)
        rows = conn.execute(
            f"""
            SELECT * FROM node_traces
            WHERE run_id IN ({placeholders})
            ORDER BY started_at, id
            """,
            tuple(run_ids),
        ).fetchall()
        return rows_to_models(rows, NodeTraceRow)
