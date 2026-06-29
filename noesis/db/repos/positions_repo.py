import sqlite3

from noesis.db.models import PositionRow
from noesis.db.repos._mapping import row_to_model, rows_to_models


class PositionsRepo:
    def insert(self, row: PositionRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO positions(
              id, user_id, symbol, market, name, kind, qty, cost_basis,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.id,
                row.user_id,
                row.symbol,
                row.market,
                row.name,
                row.kind,
                row.qty,
                row.cost_basis,
                row.created_at,
                row.updated_at,
            ),
        )

    def get(self, id: str, *, conn: sqlite3.Connection) -> PositionRow | None:
        row = conn.execute("SELECT * FROM positions WHERE id = ?", (id,)).fetchone()
        return row_to_model(row, PositionRow)

    def list_by_identity(
        self,
        user_id: str,
        label: str,
        market: str,
        kind: str,
        *,
        conn: sqlite3.Connection,
    ) -> list[PositionRow]:
        rows = conn.execute(
            """
            SELECT * FROM positions
            WHERE user_id = ?
              AND lower(market) = lower(?)
              AND kind = ?
              AND (
                lower(symbol) = lower(?)
                OR lower(coalesce(name, '')) = lower(?)
              )
            ORDER BY created_at, id
            """,
            (user_id, market, kind, label, label),
        ).fetchall()
        return rows_to_models(rows, PositionRow)

    def list_by_user(self, user_id: str, *, conn: sqlite3.Connection) -> list[PositionRow]:
        rows = conn.execute(
            "SELECT * FROM positions WHERE user_id = ? ORDER BY created_at, id",
            (user_id,),
        ).fetchall()
        return rows_to_models(rows, PositionRow)
