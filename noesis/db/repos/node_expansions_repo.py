import sqlite3

from noesis.db.models import NodeExpansionRow
from noesis.db.repos._mapping import row_to_model


class NodeExpansionsRepo:
    def get(self, entity_id: str, *, conn: sqlite3.Connection) -> NodeExpansionRow | None:
        row = conn.execute(
            "SELECT * FROM node_expansions WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        return row_to_model(row, NodeExpansionRow)

    def upsert(self, row: NodeExpansionRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO node_expansions(
              entity_id, researched, researched_at, cached_run_id, created_at,
              updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
              researched = excluded.researched,
              researched_at = excluded.researched_at,
              cached_run_id = excluded.cached_run_id,
              updated_at = excluded.updated_at
            """,
            (
                row.entity_id,
                row.researched,
                row.researched_at,
                row.cached_run_id,
                row.created_at,
                row.updated_at,
            ),
        )

    def mark_researched(
        self,
        entity_id: str,
        run_id: str,
        at: str,
        *,
        conn: sqlite3.Connection,
    ) -> None:
        conn.execute(
            """
            INSERT INTO node_expansions(
              entity_id, researched, researched_at, cached_run_id, created_at,
              updated_at
            ) VALUES (?, 1, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
              researched = 1,
              researched_at = excluded.researched_at,
              cached_run_id = excluded.cached_run_id,
              updated_at = excluded.updated_at
            """,
            (entity_id, at, run_id, at, at),
        )
