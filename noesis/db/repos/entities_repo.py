import sqlite3

from noesis.db.models import EntityRow
from noesis.db.repos._mapping import row_to_model


class EntitiesRepo:
    def upsert(self, row: EntityRow, *, conn: sqlite3.Connection) -> EntityRow:
        symbol = row.identifiers().get("symbol")
        existing = None
        if symbol is not None:
            existing = self.find_by_symbol(row.market, symbol, conn=conn)
        if existing is None:
            existing = self._find_by_market_name(row.market, row.name, conn=conn)
        if existing is not None:
            return existing
        self._insert(row, conn=conn)
        return row

    def get(self, id: str, *, conn: sqlite3.Connection) -> EntityRow | None:
        row = conn.execute("SELECT * FROM entities WHERE id = ?", (id,)).fetchone()
        return row_to_model(row, EntityRow)

    def find_by_symbol(
        self, market: str | None, symbol: str, *, conn: sqlite3.Connection
    ) -> EntityRow | None:
        row = conn.execute(
            """
            SELECT * FROM entities
            WHERE ((market = ?) OR (market IS NULL AND ? IS NULL))
              AND json_extract(identifiers_json, '$.symbol') = ?
            LIMIT 1
            """,
            (market, market, symbol),
        ).fetchone()
        return row_to_model(row, EntityRow)

    def _find_by_market_name(
        self, market: str | None, name: str, *, conn: sqlite3.Connection
    ) -> EntityRow | None:
        row = conn.execute(
            """
            SELECT * FROM entities
            WHERE ((market = ?) OR (market IS NULL AND ? IS NULL)) AND name = ?
            LIMIT 1
            """,
            (market, market, name),
        ).fetchone()
        return row_to_model(row, EntityRow)

    def _insert(self, row: EntityRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO entities(
              id, node_type, name, aliases_json, identifiers_json, market,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.id,
                row.node_type,
                row.name,
                row.aliases_json,
                row.identifiers_json,
                row.market,
                row.created_at,
                row.updated_at,
            ),
        )
