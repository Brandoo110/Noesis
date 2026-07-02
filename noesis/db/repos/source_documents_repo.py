import sqlite3

from noesis.db.models import SourceDocumentRow
from noesis.db.repos._mapping import row_to_model, rows_to_models


class SourceDocumentsRepo:
    def insert_many(
        self, rows: list[SourceDocumentRow], *, conn: sqlite3.Connection
    ) -> None:
        conn.executemany(
            """
            INSERT INTO source_documents(
              id, run_id, entity_id, url, title, publisher, published_at,
              fetched_at, source_type, reliability, content_hash, source_tier,
              created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.id,
                    row.run_id,
                    row.entity_id,
                    row.url,
                    row.title,
                    row.publisher,
                    row.published_at,
                    row.fetched_at,
                    row.source_type,
                    row.reliability,
                    row.content_hash,
                    row.source_tier,
                    row.created_at,
                )
                for row in rows
            ],
        )

    def list_by_run(
        self, run_id: str, *, conn: sqlite3.Connection
    ) -> list[SourceDocumentRow]:
        rows = conn.execute(
            """
            SELECT * FROM source_documents
            WHERE run_id = ?
            ORDER BY fetched_at, id
            """,
            (run_id,),
        ).fetchall()
        return rows_to_models(rows, SourceDocumentRow)

    def get_by_content_hash(
        self, content_hash: str, *, conn: sqlite3.Connection
    ) -> SourceDocumentRow | None:
        row = conn.execute(
            """
            SELECT * FROM source_documents
            WHERE content_hash = ?
            ORDER BY fetched_at DESC, id DESC
            LIMIT 1
            """,
            (content_hash,),
        ).fetchone()
        return row_to_model(row, SourceDocumentRow)
