import sqlite3

from noesis.db.models import HoldingRelevanceRow
from noesis.db.repos._mapping import rows_to_models


class HoldingRelevancesRepo:
    def upsert(self, row: HoldingRelevanceRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO holding_relevances(
              id, entity_id, position_id, path_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              entity_id = excluded.entity_id,
              position_id = excluded.position_id,
              path_json = excluded.path_json,
              created_at = excluded.created_at
            """,
            (
                row.id,
                row.entity_id,
                row.position_id,
                row.path_json,
                row.created_at,
            ),
        )

    def list_by_entity(
        self, entity_id: str, *, conn: sqlite3.Connection
    ) -> list[HoldingRelevanceRow]:
        rows = conn.execute(
            """
            SELECT * FROM holding_relevances
            WHERE entity_id = ?
            ORDER BY created_at, id
            """,
            (entity_id,),
        ).fetchall()
        return rows_to_models(rows, HoldingRelevanceRow)
