import sqlite3

from noesis.db.models import EvidenceRow
from noesis.db.repos._mapping import row_to_model, rows_to_models


class EvidencesRepo:
    def insert_many(self, rows: list[EvidenceRow], *, conn: sqlite3.Connection) -> None:
        conn.executemany(
            """
            INSERT INTO evidences(
              id, run_id, entity_id, source, source_tier, url, title, snippet,
              captured_at, published_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.id,
                    row.run_id,
                    row.entity_id,
                    row.source,
                    row.source_tier,
                    row.url,
                    row.title,
                    row.snippet,
                    row.captured_at,
                    row.published_at,
                    row.created_at,
                )
                for row in rows
            ],
        )

    def get(self, id: str, *, conn: sqlite3.Connection) -> EvidenceRow | None:
        row = conn.execute("SELECT * FROM evidences WHERE id = ?", (id,)).fetchone()
        return row_to_model(row, EvidenceRow)

    def list_by_run(self, run_id: str, *, conn: sqlite3.Connection) -> list[EvidenceRow]:
        rows = conn.execute(
            "SELECT * FROM evidences WHERE run_id = ? ORDER BY captured_at, id",
            (run_id,),
        ).fetchall()
        return rows_to_models(rows, EvidenceRow)
