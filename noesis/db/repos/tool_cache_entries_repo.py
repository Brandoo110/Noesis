import sqlite3

from noesis.db.models import ToolCacheEntryRow
from noesis.db.repos._mapping import row_to_model


class ToolCacheEntriesRepo:
    def upsert(self, row: ToolCacheEntryRow, *, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO tool_cache_entries(
              id, cache_key, tool_name, cache_policy, ttl_seconds, expires_at,
              hit_count, last_hit_at, payload_hash, payload_json, created_at,
              updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
              tool_name = excluded.tool_name,
              cache_policy = excluded.cache_policy,
              ttl_seconds = excluded.ttl_seconds,
              expires_at = excluded.expires_at,
              hit_count = excluded.hit_count,
              last_hit_at = excluded.last_hit_at,
              payload_hash = excluded.payload_hash,
              payload_json = excluded.payload_json,
              updated_at = excluded.updated_at
            """,
            (
                row.id,
                row.cache_key,
                row.tool_name,
                row.cache_policy,
                row.ttl_seconds,
                row.expires_at,
                row.hit_count,
                row.last_hit_at,
                row.payload_hash,
                row.payload_json,
                row.created_at,
                row.updated_at,
            ),
        )

    def get_by_key(
        self, cache_key: str, *, conn: sqlite3.Connection
    ) -> ToolCacheEntryRow | None:
        row = conn.execute(
            """
            SELECT * FROM tool_cache_entries
            WHERE cache_key = ?
            LIMIT 1
            """,
            (cache_key,),
        ).fetchone()
        return row_to_model(row, ToolCacheEntryRow)

    def record_hit(
        self, cache_key: str, hit_at: str, *, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            """
            UPDATE tool_cache_entries
            SET hit_count = hit_count + 1,
                last_hit_at = ?,
                updated_at = ?
            WHERE cache_key = ?
            """,
            (hit_at, hit_at, cache_key),
        )
