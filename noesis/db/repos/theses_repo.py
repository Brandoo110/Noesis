import sqlite3

from noesis.db.models import ThesisRow
from noesis.db.repos._mapping import row_to_model


class ThesesRepo:
    def insert(self, row: ThesisRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO theses(
              id, position_id, run_id, summary, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.id,
                row.position_id,
                row.run_id,
                row.summary,
                row.status,
                row.created_at,
                row.updated_at,
            ),
        )

    def get(self, id: str, *, conn: sqlite3.Connection) -> ThesisRow | None:
        row = conn.execute("SELECT * FROM theses WHERE id = ?", (id,)).fetchone()
        return row_to_model(row, ThesisRow)

    def latest_for_position(
        self, position_id: str, *, conn: sqlite3.Connection
    ) -> ThesisRow | None:
        row = conn.execute(
            """
            SELECT * FROM theses
            WHERE position_id = ?
            ORDER BY
              CASE WHEN status = 'confirmed' THEN 0 ELSE 1 END,
              created_at DESC,
              updated_at DESC,
              id DESC
            LIMIT 1
            """,
            (position_id,),
        ).fetchone()
        return row_to_model(row, ThesisRow)

    def set_status(
        self, id: str, status: str, updated_at: str, *, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            "UPDATE theses SET status = ?, updated_at = ? WHERE id = ?",
            (status, updated_at, id),
        )
