from urllib.parse import urlparse

import httpx

from noesis.graph.errors import IngestError
from noesis.graph.schemas import IngestedDoc


class TavilySearchAdapter:
    def __init__(self, api_key: str, *, endpoint: str = "https://api.tavily.com/search") -> None:
        self.api_key = api_key
        self.endpoint = endpoint

    def search(self, query: str, *, limit: int = 8) -> list[IngestedDoc]:
        if not self.api_key.strip():
            raise IngestError("Tavily API key is not configured", reason="missing_key")

        try:
            response = httpx.post(
                self.endpoint,
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": limit,
                },
                timeout=20.0,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise IngestError("Tavily search failed", reason=str(exc)) from exc

        results = payload.get("results", [])
        if not isinstance(results, list):
            raise IngestError("Tavily response has invalid results", reason="bad_payload")

        docs: list[IngestedDoc] = []
        for item in results[:limit]:
            if not isinstance(item, dict):
                continue
            doc = self._doc_from_result(item)
            if doc is not None:
                docs.append(doc)
        return docs

    def _doc_from_result(self, item: dict[str, object]) -> IngestedDoc | None:
        url = item.get("url")
        title = item.get("title")
        content = item.get("content") or item.get("raw_content")
        if not isinstance(content, str) or not content.strip():
            return None
        return IngestedDoc(
            source="tavily",
            source_tier=self._tier_for_url(url if isinstance(url, str) else None),
            title=title if isinstance(title, str) else None,
            url=url if isinstance(url, str) else None,
            text=content,
            published_at=None,
        )

    def _tier_for_url(self, url: str | None) -> int:
        if url is None:
            return 3
        host = urlparse(url).netloc.lower()
        if any(part in host for part in ("sec.gov", "investor", "ir.")):
            return 1
        if any(part in host for part in ("bloomberg", "reuters", "ft.com", "wsj")):
            return 2
        return 3
