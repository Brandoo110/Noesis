import sqlite3

from noesis.db.models import IntelItemRow
from noesis.db.repos._mapping import rows_to_models


class IntelItemsRepo:
    def insert_many(self, rows: list[IntelItemRow], *, conn: sqlite3.Connection) -> None:
        conn.executemany(
            """
            INSERT INTO intel_items(
              id, entity_id, run_id, source, source_tier, title, content, url,
              published_at, sentiment_json, event_type, evidence_ids_json,
              created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.id,
                    row.entity_id,
                    row.run_id,
                    row.source,
                    row.source_tier,
                    row.title,
                    row.content,
                    row.url,
                    row.published_at,
                    row.sentiment_json,
                    row.event_type,
                    row.evidence_ids_json,
                    row.created_at,
                )
                for row in rows
            ],
        )

    def list_by_entity(
        self, entity_id: str, *, conn: sqlite3.Connection
    ) -> list[IntelItemRow]:
        rows = conn.execute(
            "SELECT * FROM intel_items WHERE entity_id = ? ORDER BY created_at, id",
            (entity_id,),
        ).fetchall()
        return rows_to_models(rows, IntelItemRow)
