import sqlite3

from noesis.db.models import RunRow
from noesis.db.repos._mapping import row_to_model, rows_to_models


class RunRegistryRepo:
    def insert(self, row: RunRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO run_registry(
              id, position_id, entity_id, node_kind, status, started_at,
              ended_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.id,
                row.position_id,
                row.entity_id,
                row.node_kind,
                row.status,
                row.started_at,
                row.ended_at,
                row.created_at,
            ),
        )

    def get(self, id: str, *, conn: sqlite3.Connection) -> RunRow | None:
        row = conn.execute("SELECT * FROM run_registry WHERE id = ?", (id,)).fetchone()
        return row_to_model(row, RunRow)

    def get_seed_entity_id(
        self, position_id: str, *, conn: sqlite3.Connection
    ) -> str | None:
        row = conn.execute(
            """
            SELECT entity_id FROM run_registry
            WHERE position_id = ?
              AND node_kind = 'seed'
              AND entity_id IS NOT NULL
            ORDER BY started_at DESC, created_at DESC, id DESC
            LIMIT 1
            """,
            (position_id,),
        ).fetchone()
        return str(row["entity_id"]) if row is not None else None

    def latest_seed_for_position(
        self, position_id: str, *, conn: sqlite3.Connection
    ) -> RunRow | None:
        row = conn.execute(
            """
            SELECT * FROM run_registry
            WHERE position_id = ?
              AND node_kind = 'seed'
            ORDER BY started_at DESC, created_at DESC, id DESC
            LIMIT 1
            """,
            (position_id,),
        ).fetchone()
        return row_to_model(row, RunRow)

    def latest_seed_for_positions(
        self, position_ids: list[str], *, conn: sqlite3.Connection
    ) -> list[RunRow]:
        if not position_ids:
            return []
        placeholders = ", ".join("?" for _ in position_ids)
        rows = conn.execute(
            f"""
            WITH ranked AS (
              SELECT
                id, position_id, entity_id, node_kind, status, started_at,
                ended_at, created_at,
                ROW_NUMBER() OVER (
                  PARTITION BY position_id
                  ORDER BY started_at DESC, created_at DESC, id DESC
                ) AS rn
              FROM run_registry
              WHERE node_kind = 'seed'
                AND position_id IN ({placeholders})
            )
            SELECT
              id, position_id, entity_id, node_kind, status, started_at,
              ended_at, created_at
            FROM ranked
            WHERE rn = 1
            ORDER BY started_at DESC, created_at DESC, id DESC
            """,
            tuple(position_ids),
        ).fetchall()
        return rows_to_models(rows, RunRow)

    def list_ids_by_position(
        self, position_id: str, *, conn: sqlite3.Connection
    ) -> list[str]:
        rows = conn.execute(
            """
            SELECT id FROM run_registry
            WHERE position_id = ?
            ORDER BY started_at DESC, created_at DESC, id DESC
            """,
            (position_id,),
        ).fetchall()
        return [str(row["id"]) for row in rows]

    def set_entity(
        self, id: str, entity_id: str, *, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            "UPDATE run_registry SET entity_id = ? WHERE id = ?",
            (entity_id, id),
        )

    def set_status(
        self, id: str, status: str, ended_at: str | None, *, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            "UPDATE run_registry SET status = ?, ended_at = ? WHERE id = ?",
            (status, ended_at, id),
        )
