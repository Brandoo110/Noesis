import sqlite3

from noesis.db.models import GraphEdgeRow
from noesis.db.repos._mapping import rows_to_models


class GraphEdgesRepo:
    def insert_many(self, rows: list[GraphEdgeRow], *, conn: sqlite3.Connection) -> None:
        conn.executemany(
            """
            INSERT INTO graph_edges(
              id, from_entity_id, to_entity_id, relation, basis, confidence,
              evidence_ids_json, run_id, rationale, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.id,
                    row.from_entity_id,
                    row.to_entity_id,
                    row.relation,
                    row.basis,
                    row.confidence,
                    row.evidence_ids_json,
                    row.run_id,
                    row.rationale,
                    row.created_at,
                )
                for row in rows
            ],
        )

    def list_from(self, entity_id: str, *, conn: sqlite3.Connection) -> list[GraphEdgeRow]:
        rows = conn.execute(
            """
            SELECT * FROM graph_edges
            WHERE from_entity_id = ?
            ORDER BY created_at, id
            """,
            (entity_id,),
        ).fetchall()
        return rows_to_models(rows, GraphEdgeRow)

    def list_to(self, entity_id: str, *, conn: sqlite3.Connection) -> list[GraphEdgeRow]:
        rows = conn.execute(
            """
            SELECT * FROM graph_edges
            WHERE to_entity_id = ?
            ORDER BY created_at, id
            """,
            (entity_id,),
        ).fetchall()
        return rows_to_models(rows, GraphEdgeRow)

    def delete(self, id: str, *, conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM graph_edges WHERE id = ?", (id,))
