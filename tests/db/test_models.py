from noesis.db.models import (
    ApprovalRow,
    EntityRow,
    EvidenceRow,
    IntelItemRow,
    NodeTraceRow,
    PositionRow,
    RunRow,
    ThesisAssumptionRow,
    ThesisRow,
)
from noesis.graph.schemas import SentimentTag


NOW = "2026-06-26T00:00:00Z"


def test_position_row_validates_complete_dict() -> None:
    row = PositionRow.model_validate(
        {
            "id": "position-1",
            "user_id": "user-1",
            "symbol": "AAPL",
            "market": "US",
            "name": "Apple",
            "kind": "owned",
            "qty": 1.5,
            "cost_basis": 100.0,
            "created_at": NOW,
            "updated_at": NOW,
        }
    )

    assert row.symbol == "AAPL"


def test_entity_row_parses_json_fields() -> None:
    row = EntityRow.model_validate(
        {
            "id": "entity-1",
            "node_type": "company",
            "name": "Apple",
            "aliases_json": '["AAPL", "Apple Inc."]',
            "identifiers_json": '{"symbol": "AAPL", "cik": "0000320193"}',
            "market": "US",
            "created_at": NOW,
            "updated_at": NOW,
        }
    )

    assert row.aliases() == ["AAPL", "Apple Inc."]
    assert row.identifiers() == {"symbol": "AAPL", "cik": "0000320193"}


def test_run_row_validates_complete_dict() -> None:
    row = RunRow.model_validate(
        {
            "id": "run-1",
            "position_id": "position-1",
            "entity_id": "entity-1",
            "node_kind": "seed",
            "status": "running",
            "started_at": NOW,
            "ended_at": None,
            "created_at": NOW,
        }
    )

    assert row.status == "running"


def test_node_trace_row_parses_evidence_ids() -> None:
    row = NodeTraceRow.model_validate(
        {
            "id": "trace-1",
            "run_id": "run-1",
            "node_name": "intel_synth",
            "entity_id": "entity-1",
            "inputs_ref": "input",
            "outputs_ref": "output",
            "status": "success",
            "reason": None,
            "fallback_used": None,
            "model_id": "fake",
            "evidence_ids_json": '["evidence-1"]',
            "started_at": NOW,
            "ended_at": NOW,
            "created_at": NOW,
        }
    )

    assert row.evidence_ids() == ["evidence-1"]


def test_evidence_row_validates_complete_dict() -> None:
    row = EvidenceRow.model_validate(
        {
            "id": "evidence-1",
            "run_id": "run-1",
            "entity_id": "entity-1",
            "source": "web",
            "source_tier": 2,
            "url": "https://example.com",
            "title": "Evidence",
            "snippet": "Evidence snippet",
            "captured_at": NOW,
            "published_at": None,
            "created_at": NOW,
        }
    )

    assert row.snippet == "Evidence snippet"


def test_intel_item_row_parses_sentiment_and_evidence_ids() -> None:
    row = IntelItemRow.model_validate(
        {
            "id": "intel-1",
            "entity_id": "entity-1",
            "run_id": "run-1",
            "source": "web",
            "source_tier": 2,
            "title": "Intel",
            "content": "Intel content",
            "url": "https://example.com",
            "published_at": None,
            "sentiment_json": '{"dir": "neutral", "conf": 0.7}',
            "event_type": "news",
            "evidence_ids_json": '["evidence-1"]',
            "created_at": NOW,
        }
    )

    assert row.sentiment() == SentimentTag(dir="neutral", conf=0.7)
    assert row.evidence_ids() == ["evidence-1"]


def test_thesis_row_validates_complete_dict() -> None:
    row = ThesisRow.model_validate(
        {
            "id": "thesis-1",
            "position_id": "position-1",
            "run_id": "run-1",
            "summary": "Thesis",
            "status": "draft",
            "created_at": NOW,
            "updated_at": NOW,
        }
    )

    assert row.summary == "Thesis"


def test_thesis_assumption_row_parses_evidence_ids() -> None:
    row = ThesisAssumptionRow.model_validate(
        {
            "id": "assumption-1",
            "thesis_id": "thesis-1",
            "text": "Risk assumption",
            "kind": "risk",
            "evidence_ids_json": '["evidence-1"]',
            "status": "draft",
            "created_at": NOW,
        }
    )

    assert row.evidence_ids() == ["evidence-1"]


def test_approval_row_parses_payload() -> None:
    row = ApprovalRow.model_validate(
        {
            "id": "approval-1",
            "run_id": "run-1",
            "object_type": "thesis",
            "object_id": "thesis-1",
            "status": "pending",
            "payload_json": '{"summary": "Draft"}',
            "created_at": NOW,
            "updated_at": NOW,
        }
    )

    assert row.payload() == {"summary": "Draft"}
