from collections.abc import Callable
from sqlite3 import Connection

from noesis.graph.schemas import EvidenceRecord


class EvidenceRetriever:
    def __init__(self, chroma_dir: str, conn_factory: Callable[[], Connection]) -> None:
        self.chroma_dir = chroma_dir
        self.conn_factory = conn_factory
        self.collection = self._build_collection()
        self.records: dict[str, EvidenceRecord] = {}
        self.rowids_by_id: dict[str, int] = {}
        self.ids_by_rowid: dict[int, str] = {}
        self.next_rowid = 1

    def index(self, evidences: list[EvidenceRecord]) -> None:
        new_evidences = [item for item in evidences if item.id not in self.records]
        if not new_evidences:
            return
        rows: list[tuple[int, str, str, str | None]] = []
        for item in new_evidences:
            rowid = self.next_rowid
            self.next_rowid += 1
            self.records[item.id] = item
            self.rowids_by_id[item.id] = rowid
            self.ids_by_rowid[rowid] = item.id
            rows.append((rowid, item.id, item.snippet, item.title))
        conn = self.conn_factory()
        conn.executemany(
            """
            INSERT INTO evidences_fts(rowid, evidence_id, snippet, title)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        if self.collection is not None:
            self._index_chroma(new_evidences)

    def retrieve(
        self, query: str, *, run_id: str, top_k: int = 6
    ) -> list[EvidenceRecord]:
        matches: list[EvidenceRecord] = []
        seen: set[str] = set()
        for item in self._retrieve_fts(query, top_k=top_k):
            if item.id not in seen:
                matches.append(item)
                seen.add(item.id)
        if self.collection is not None and len(matches) < top_k:
            for item in self._retrieve_chroma(query, top_k=top_k):
                if item.id not in seen:
                    matches.append(item)
                    seen.add(item.id)
                if len(matches) >= top_k:
                    break
        return [item for item in matches if item.source][:top_k]

    def _build_collection(self) -> object | None:
        try:
            import chromadb
        except ImportError:
            return None
        try:
            client = chromadb.PersistentClient(path=self.chroma_dir)
            return client.get_or_create_collection("evidences_v1")
        except Exception:
            return None

    def _index_chroma(self, evidences: list[EvidenceRecord]) -> None:
        if self.collection is None or not evidences:
            return
        try:
            self.collection.upsert(
                ids=[item.id for item in evidences],
                documents=[item.snippet for item in evidences],
                metadatas=[
                    {
                        "source": item.source,
                        "source_tier": item.source_tier,
                        "url": item.url or "",
                        "title": item.title or "",
                        "captured_at": item.captured_at,
                        "published_at": item.published_at or "",
                    }
                    for item in evidences
                ],
            )
        except Exception:
            self.collection = None

    def _retrieve_fts(self, query: str, *, top_k: int) -> list[EvidenceRecord]:
        conn = self.conn_factory()
        rows = conn.execute(
            """
            SELECT rowid
            FROM evidences_fts
            WHERE evidences_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, top_k),
        ).fetchall()
        matches: list[EvidenceRecord] = []
        for row in rows:
            evidence_id = self.ids_by_rowid.get(int(row["rowid"]))
            if evidence_id is None:
                continue
            record = self.records.get(evidence_id)
            if record is not None:
                matches.append(record)
        return matches

    def _retrieve_chroma(self, query: str, *, top_k: int) -> list[EvidenceRecord]:
        if self.collection is None:
            return []
        try:
            result = self.collection.query(query_texts=[query], n_results=top_k)
        except Exception:
            return []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        matches: list[EvidenceRecord] = []
        for evidence_id, doc, metadata in zip(ids, docs, metadatas, strict=False):
            if not isinstance(evidence_id, str) or not isinstance(doc, str):
                continue
            data = metadata if isinstance(metadata, dict) else {}
            matches.append(
                EvidenceRecord(
                    id=evidence_id,
                    source=str(data.get("source", "chroma")),
                    source_tier=int(data.get("source_tier", 3)),
                    url=str(data.get("url") or "") or None,
                    title=str(data.get("title") or "") or None,
                    snippet=doc,
                    captured_at=str(data.get("captured_at") or ""),
                    published_at=str(data.get("published_at") or "") or None,
                )
            )
        return matches
