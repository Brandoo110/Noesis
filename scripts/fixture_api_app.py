"""Fixture FastAPI app for isolated UI smoke runs."""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from noesis.api.app import create_app
from noesis.api.deps import _checkpoint_path, get_graph_deps
from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.graph.runner import build_graph_deps
from noesis.graph.schemas import IngestedDoc
from noesis.tools.llm.router import LLMRole
from noesis.tools.search.fake import FakeSearchAdapter


class FixtureLLM:
    def available(self, role: LLMRole) -> bool:
        return True

    def complete_json(
        self, role: LLMRole, prompt: str, schema: type[BaseModel]
    ) -> BaseModel:
        if schema.__name__ == "ResolvedEntity":
            return schema.model_validate(
                {
                    "entity_id": "entity-noeui",
                    "node_type": "company",
                    "name": "Noesis UI Fixture",
                    "aliases": ["NOEUI"],
                    "identifiers": {"symbol": "NOEUI"},
                    "market": "US",
                }
            )
        evidence_id = _first_evidence_id(prompt)
        if schema.__name__ == "IntelSynthPayload":
            return schema.model_validate(
                {
                    "items": [
                        {
                            "title": "Fixture demand signal",
                            "content": "Fixture evidence shows a stable research signal.",
                            "event_type": "demand",
                            "source": "web",
                            "source_tier": 2,
                            "url": "https://example.com/noesis-ui-fixture",
                            "published_at": None,
                            "sentiment": {"dir": "neutral", "conf": 0.72},
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
                            "to_name": "Fixture Supplier",
                            "to_symbol": "FIXSUP",
                            "to_node_type": "company",
                            "relation": "supplier",
                            "basis": "source_backed",
                            "confidence": 0.8,
                            "evidence_ids": [evidence_id],
                            "rationale": "Fixture supplier link is cited in evidence.",
                        }
                    ]
                }
            )
        return schema.model_validate(
            {
                "summary": "NOEUI has a fixture-backed thesis for UI smoke validation.",
                "assumptions": [
                    {
                        "text": "The fixture signal remains evidence-backed.",
                        "kind": "assumption",
                        "evidence_ids": [evidence_id],
                    }
                ],
            }
        )

    def complete_text(self, role: LLMRole, prompt: str) -> str:
        return "{}"


def fixture_graph_deps() -> Iterator[object]:
    db_path = os.environ["NOESIS_FIXTURE_DB_PATH"]
    chroma_dir = os.environ["NOESIS_FIXTURE_CHROMA_DIR"]
    Path(chroma_dir).mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    checkpoint_conn = sqlite3.connect(_checkpoint_path(db_path), check_same_thread=False)
    try:
        migrate(conn)
        yield build_graph_deps(
            conn=conn,
            checkpoint_conn=checkpoint_conn,
            chroma_dir=chroma_dir,
            search=FakeSearchAdapter(
                [
                    IngestedDoc(
                        source="web",
                        source_tier=2,
                        title="Fixture research signal",
                        url="https://example.com/noesis-ui-fixture",
                        text="Fixture evidence shows a stable research signal.",
                    )
                ]
            ),
            llm=FixtureLLM(),
            now=_utc_now,
        )
    finally:
        checkpoint_conn.close()
        conn.close()


def _first_evidence_id(prompt: str) -> str:
    match = re.search(r"(evidence-[a-f0-9]+)", prompt)
    if match is None:
        raise AssertionError(f"prompt did not include evidence id: {prompt}")
    return match.group(1)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


app = create_app()
app.dependency_overrides[get_graph_deps] = fixture_graph_deps
