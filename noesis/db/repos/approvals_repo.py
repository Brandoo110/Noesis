import sqlite3

from noesis.db.models import ApprovalRow
from noesis.db.repos._mapping import row_to_model


class ApprovalsRepo:
    def insert(self, row: ApprovalRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO approvals(
              id, run_id, object_type, object_id, status, payload_json,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.id,
                row.run_id,
                row.object_type,
                row.object_id,
                row.status,
                row.payload_json,
                row.created_at,
                row.updated_at,
            ),
        )

    def get_by_object(
        self, object_type: str, object_id: str, *, conn: sqlite3.Connection
    ) -> ApprovalRow | None:
        row = conn.execute(
            """
            SELECT * FROM approvals
            WHERE object_type = ? AND object_id = ?
            LIMIT 1
            """,
            (object_type, object_id),
        ).fetchone()
        return row_to_model(row, ApprovalRow)

    def set_status(
        self, id: str, status: str, updated_at: str, *, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            "UPDATE approvals SET status = ?, updated_at = ? WHERE id = ?",
            (status, updated_at, id),
        )
