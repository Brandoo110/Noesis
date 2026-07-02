from noesis.db.models import (
    ApprovalRow,
    EntityRow,
    EvidenceRow,
    GraphEdgeRow,
    HoldingRelevanceRow,
    IntelItemRow,
    NodeExpansionRow,
    NodeTraceRow,
    PositionRow,
    RunRow,
    SourceDocumentRow,
    ThesisAssumptionRow,
    ThesisRow,
    ToolCacheEntryRow,
    ToolInvocationRow,
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


def test_graph_edge_row_parses_evidence_ids() -> None:
    row = GraphEdgeRow.model_validate(
        {
            "id": "edge-1",
            "from_entity_id": "entity-aapl",
            "to_entity_id": "entity-tsmc",
            "relation": "supplier",
            "basis": "source_backed",
            "confidence": 0.8,
            "evidence_ids_json": '["evidence-1", "evidence-2"]',
            "run_id": "run-1",
            "rationale": "TSMC supplies chips to Apple.",
            "created_at": NOW,
        }
    )

    assert row.from_entity_id == "entity-aapl"
    assert row.evidence_ids() == ["evidence-1", "evidence-2"]


def test_node_expansion_row_validates_complete_dict() -> None:
    row = NodeExpansionRow.model_validate(
        {
            "entity_id": "entity-aapl",
            "researched": 1,
            "researched_at": NOW,
            "cached_run_id": "run-1",
            "created_at": NOW,
            "updated_at": NOW,
        }
    )

    assert row.entity_id == "entity-aapl"
    assert row.researched == 1


def test_holding_relevance_row_parses_path() -> None:
    row = HoldingRelevanceRow.model_validate(
        {
            "id": "relevance-1",
            "entity_id": "entity-tsmc",
            "position_id": "position-1",
            "path_json": '["entity-tsmc", "entity-aapl"]',
            "created_at": NOW,
        }
    )

    assert row.path() == ["entity-tsmc", "entity-aapl"]


def test_source_document_row_validates_agentops_metadata() -> None:
    row = SourceDocumentRow.model_validate(
        {
            "id": "source-doc-1",
            "run_id": "run-1",
            "entity_id": "entity-aapl",
            "url": "https://example.com/apple",
            "title": "Apple supplier update",
            "publisher": "Example News",
            "published_at": "2026-06-25T00:00:00Z",
            "fetched_at": NOW,
            "source_type": "news",
            "reliability": 0.8,
            "content_hash": "hash-1",
            "source_tier": 2,
            "created_at": NOW,
        }
    )

    assert row.publisher == "Example News"
    assert row.content_hash == "hash-1"


def test_tool_invocation_row_validates_metrics_fields() -> None:
    row = ToolInvocationRow.model_validate(
        {
            "id": "tool-call-1",
            "run_id": "run-1",
            "trace_id": "trace-1",
            "tool_name": "search.web",
            "status": "success",
            "permission_level": "network",
            "input_summary": "query=AAPL supplier",
            "output_summary": "8 docs",
            "error_message": None,
            "cache_key": "search:AAPL",
            "cache_hit": 0,
            "retry_count": 1,
            "latency_ms": 240,
            "token_input": 100,
            "token_output": 40,
            "estimated_cost_usd": 0.0012,
            "started_at": NOW,
            "ended_at": NOW,
            "created_at": NOW,
        }
    )

    assert row.tool_name == "search.web"
    assert row.cache_hit is False
    assert row.total_tokens() == 140


def test_tool_cache_entry_row_validates_cache_policy_fields() -> None:
    row = ToolCacheEntryRow.model_validate(
        {
            "id": "cache-1",
            "cache_key": "search:AAPL",
            "tool_name": "search.web",
            "cache_policy": "ttl",
            "ttl_seconds": 86400,
            "expires_at": "2026-06-27T00:00:00Z",
            "hit_count": 2,
            "last_hit_at": NOW,
            "payload_hash": "payload-hash",
            "payload_json": '{"ok": true}',
            "created_at": NOW,
            "updated_at": NOW,
        }
    )

    assert row.hit_count == 2
    assert row.cache_policy == "ttl"
    assert row.payload_json == '{"ok": true}'
