import sqlite3

from noesis.db.models import ThesisAssumptionRow
from noesis.db.repos._mapping import rows_to_models


class ThesisAssumptionsRepo:
    def insert_many(
        self, rows: list[ThesisAssumptionRow], *, conn: sqlite3.Connection
    ) -> None:
        conn.executemany(
            """
            INSERT INTO thesis_assumptions(
              id, thesis_id, text, kind, evidence_ids_json, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.id,
                    row.thesis_id,
                    row.text,
                    row.kind,
                    row.evidence_ids_json,
                    row.status,
                    row.created_at,
                )
                for row in rows
            ],
        )

    def list_by_thesis(
        self, thesis_id: str, *, conn: sqlite3.Connection
    ) -> list[ThesisAssumptionRow]:
        rows = conn.execute(
            """
            SELECT * FROM thesis_assumptions
            WHERE thesis_id = ? ORDER BY created_at, id
            """,
            (thesis_id,),
        ).fetchall()
        return rows_to_models(rows, ThesisAssumptionRow)
