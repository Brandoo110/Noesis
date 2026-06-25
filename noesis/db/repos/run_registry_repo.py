import sqlite3

from noesis.db.models import RunRow
from noesis.db.repos._mapping import row_to_model


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

    def set_status(
        self, id: str, status: str, ended_at: str | None, *, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            "UPDATE run_registry SET status = ?, ended_at = ? WHERE id = ?",
            (status, ended_at, id),
        )
