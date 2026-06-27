import sqlite3
from collections.abc import Callable

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
        return _dedupe_edges(
            rows_to_models(rows, GraphEdgeRow),
            key=lambda row: (row.to_entity_id, row.relation),
        )

    def list_to(self, entity_id: str, *, conn: sqlite3.Connection) -> list[GraphEdgeRow]:
        rows = conn.execute(
            """
            SELECT * FROM graph_edges
            WHERE to_entity_id = ?
            ORDER BY created_at, id
            """,
            (entity_id,),
        ).fetchall()
        return _dedupe_edges(
            rows_to_models(rows, GraphEdgeRow),
            key=lambda row: (row.from_entity_id, row.relation),
        )

    def delete(self, id: str, *, conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM graph_edges WHERE id = ?", (id,))


def _dedupe_edges(
    rows: list[GraphEdgeRow],
    key: Callable[[GraphEdgeRow], tuple[str, str]],
) -> list[GraphEdgeRow]:
    selected: dict[tuple[str, str], GraphEdgeRow] = {}
    for row in rows:
        row_key = key(row)
        current = selected.get(row_key)
        if current is None or _is_better_edge(row, current):
            selected[row_key] = row
    return list(selected.values())


def _is_better_edge(candidate: GraphEdgeRow, current: GraphEdgeRow) -> bool:
    candidate_priority = 1 if candidate.basis == "source_backed" else 0
    current_priority = 1 if current.basis == "source_backed" else 0
    if candidate_priority != current_priority:
        return candidate_priority > current_priority
    return candidate.confidence > current.confidence
