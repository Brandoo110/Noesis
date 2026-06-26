import re
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from noesis.api.app import create_app
from noesis.api.deps import _checkpoint_path, get_graph_deps
from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.graph.runner import build_graph_deps
from noesis.graph.schemas import IngestedDoc
from noesis.tools.llm.router import LLMRole
from noesis.tools.search.fake import FakeSearchAdapter

NOW = "2026-06-26T00:00:00Z"


@dataclass(frozen=True)
class ApiTestContext:
    client: TestClient
    db_path: Path
    checkpoint_path: Path
    chroma_dir: Path


class ApiFakeLLM:
    def available(self, role: LLMRole) -> bool:
        return True

    def complete_json(
        self, role: LLMRole, prompt: str, schema: type[BaseModel]
    ) -> BaseModel:
        if schema.__name__ == "ResolvedEntity":
            return schema.model_validate(
                {
                    "entity_id": "entity-aapl",
                    "node_type": "company",
                    "name": "Apple Inc.",
                    "aliases": ["AAPL"],
                    "identifiers": {"symbol": "AAPL"},
                    "market": "US",
                }
            )
        evidence_id = _first_evidence_id(prompt)
        if schema.__name__ == "IntelSynthPayload":
            return schema.model_validate(
                {
                    "items": [
                        {
                            "title": "Supplier pressure update",
                            "content": "Supplier pressure eased based on cited evidence.",
                            "event_type": "supply_chain",
                            "source": "web",
                            "source_tier": 2,
                            "url": "https://example.com/supplier",
                            "published_at": None,
                            "sentiment": {"dir": "neutral", "conf": 0.7},
                            "evidence_ids": [evidence_id],
                        }
                    ]
                }
            )
        if schema.__name__ == "ExpandPayload":
            return schema.model_validate(
                {
                    "edges": [
                        {
                            "to_name": "Taiwan Semiconductor Manufacturing",
                            "to_symbol": "TSM",
                            "to_node_type": "company",
                            "relation": "supplier",
                            "basis": "source_backed",
                            "confidence": 0.82,
                            "evidence_ids": [evidence_id],
                            "rationale": "Supplier relationship is cited in evidence.",
                        }
                    ]
                }
            )
        return schema.model_validate(
            {
                "summary": "AAPL may benefit as supplier pressure eases.",
                "assumptions": [
                    {
                        "text": "Apple supplier pressure remains observable in future filings.",
                        "kind": "assumption",
                        "evidence_ids": [evidence_id],
                    }
                ],
            }
        )

    def complete_text(self, role: LLMRole, prompt: str) -> str:
        return "{}"


@pytest.fixture
def api_context(tmp_path: Path) -> Iterator[ApiTestContext]:
    db_path = tmp_path / "noesis.db"
    chroma_dir = tmp_path / "chroma"
    checkpoint_path = Path(_checkpoint_path(str(db_path)))
    app = create_app()

    def override_graph_deps() -> Iterator[object]:
        conn = connect(db_path)
        checkpoint_conn = sqlite3.connect(checkpoint_path, check_same_thread=False)
        try:
            migrate(conn)
            yield build_graph_deps(
                conn=conn,
                checkpoint_conn=checkpoint_conn,
                chroma_dir=str(chroma_dir),
                search=FakeSearchAdapter(
                    [
                        IngestedDoc(
                            source="web",
                            source_tier=2,
                            title="Supplier update",
                            url="https://example.com/supplier",
                            text="Supplier pressure eased for Apple.",
                        )
                    ]
                ),
                llm=ApiFakeLLM(),
                now=lambda: NOW,
            )
        finally:
            checkpoint_conn.close()
            conn.close()

    app.dependency_overrides[get_graph_deps] = override_graph_deps
    with TestClient(app, raise_server_exceptions=False) as client:
        yield ApiTestContext(
            client=client,
            db_path=db_path,
            checkpoint_path=checkpoint_path,
            chroma_dir=chroma_dir,
        )


def _first_evidence_id(prompt: str) -> str:
    match = re.search(r"(evidence-[a-f0-9]+)", prompt)
    if match is None:
        raise AssertionError(f"prompt did not include evidence id: {prompt}")
    return match.group(1)
