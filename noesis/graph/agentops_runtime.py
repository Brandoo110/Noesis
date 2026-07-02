from dataclasses import dataclass, field
from sqlite3 import Connection

from noesis.db.models import SourceDocumentRow, ToolCacheEntryRow, ToolInvocationRow
from noesis.db.repos.source_documents_repo import SourceDocumentsRepo
from noesis.db.repos.tool_cache_entries_repo import ToolCacheEntriesRepo
from noesis.db.repos.tool_invocations_repo import ToolInvocationsRepo


@dataclass
class SourceDocumentsRuntime:
    conn: Connection
    repo: SourceDocumentsRepo = field(default_factory=SourceDocumentsRepo)

    def insert_many(
        self, rows: list[SourceDocumentRow], *, conn: Connection | None = None
    ) -> None:
        self.repo.insert_many(rows, conn=conn or self.conn)

    def list_by_run(
        self, run_id: str, *, conn: Connection | None = None
    ) -> list[SourceDocumentRow]:
        return self.repo.list_by_run(run_id, conn=conn or self.conn)

    def get_by_content_hash(
        self, content_hash: str, *, conn: Connection | None = None
    ) -> SourceDocumentRow | None:
        return self.repo.get_by_content_hash(content_hash, conn=conn or self.conn)


@dataclass
class ToolInvocationsRuntime:
    conn: Connection
    repo: ToolInvocationsRepo = field(default_factory=ToolInvocationsRepo)

    def insert(
        self, row: ToolInvocationRow, *, conn: Connection | None = None
    ) -> None:
        self.repo.insert(row, conn=conn or self.conn)

    def list_by_run(
        self, run_id: str, *, conn: Connection | None = None
    ) -> list[ToolInvocationRow]:
        return self.repo.list_by_run(run_id, conn=conn or self.conn)

    def list_by_run_ids(
        self, run_ids: list[str], *, conn: Connection | None = None
    ) -> list[ToolInvocationRow]:
        return self.repo.list_by_run_ids(run_ids, conn=conn or self.conn)


@dataclass
class ToolCacheEntriesRuntime:
    conn: Connection
    repo: ToolCacheEntriesRepo = field(default_factory=ToolCacheEntriesRepo)

    def upsert(
        self, row: ToolCacheEntryRow, *, conn: Connection | None = None
    ) -> None:
        self.repo.upsert(row, conn=conn or self.conn)

    def get_by_key(
        self, cache_key: str, *, conn: Connection | None = None
    ) -> ToolCacheEntryRow | None:
        return self.repo.get_by_key(cache_key, conn=conn or self.conn)

    def record_hit(
        self, cache_key: str, hit_at: str, *, conn: Connection | None = None
    ) -> None:
        self.repo.record_hit(cache_key, hit_at, conn=conn or self.conn)
