import sqlite3

from noesis.db.models import ToolInvocationRow
from noesis.db.repos._mapping import rows_to_models


class ToolInvocationsRepo:
    def insert(self, row: ToolInvocationRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO tool_invocations(
              id, run_id, trace_id, tool_name, status, permission_level,
              input_summary, output_summary, error_message, cache_key,
              cache_hit, retry_count, latency_ms, token_input, token_output,
              estimated_cost_usd, started_at, ended_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.id,
                row.run_id,
                row.trace_id,
                row.tool_name,
                row.status,
                row.permission_level,
                row.input_summary,
                row.output_summary,
                row.error_message,
                row.cache_key,
                1 if row.cache_hit else 0,
                row.retry_count,
                row.latency_ms,
                row.token_input,
                row.token_output,
                row.estimated_cost_usd,
                row.started_at,
                row.ended_at,
                row.created_at,
            ),
        )

    def list_by_run(
        self, run_id: str, *, conn: sqlite3.Connection
    ) -> list[ToolInvocationRow]:
        rows = conn.execute(
            """
            SELECT * FROM tool_invocations
            WHERE run_id = ?
            ORDER BY started_at, rowid
            """,
            (run_id,),
        ).fetchall()
        return rows_to_models(rows, ToolInvocationRow)

    def list_by_run_ids(
        self, run_ids: list[str], *, conn: sqlite3.Connection
    ) -> list[ToolInvocationRow]:
        if not run_ids:
            return []
        placeholders = ", ".join("?" for _ in run_ids)
        rows = conn.execute(
            f"""
            SELECT * FROM tool_invocations
            WHERE run_id IN ({placeholders})
            ORDER BY started_at, rowid
            """,
            tuple(run_ids),
        ).fetchall()
        return rows_to_models(rows, ToolInvocationRow)
