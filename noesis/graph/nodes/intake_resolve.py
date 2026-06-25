import json
import re

from noesis.db.models import EntityRow
from noesis.graph.errors import EntityResolveError
from noesis.graph.schemas import DegradeNote, PositionInput, ResolvedEntity
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate
from noesis.tools.llm.router import LLMRole

REQUIRED_STATE_KEYS = ("raw_input",)
OUTPUT_STATE_KEYS = ("resolved_entity", "entity_id", "degraded")
SYMBOL_ALIASES = ("ticker", "code")


def intake_resolve(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    raw_input = state.get("raw_input")
    if raw_input is None:
        raise EntityResolveError("raw_input is required", reason="missing_raw_input")
    existing = deps.repos.entities.find_by_symbol(raw_input.market, raw_input.symbol)
    if existing is not None:
        resolved = _row_to_resolved(existing)
        return {"resolved_entity": resolved, "entity_id": resolved.entity_id, "degraded": state.get("degraded", [])}
    degraded = list(state.get("degraded", []))
    if deps.llm.available(LLMRole.LIGHT):
        resolved = deps.llm.complete_json(LLMRole.LIGHT, _prompt(raw_input), ResolvedEntity)
        resolved = _normalize_entity_identifiers(resolved)
    else:
        resolved = _fallback_entity(raw_input)
        degraded.append(
            DegradeNote(
                node_name="intake_resolve",
                reason="light_llm_unavailable",
                fallback_used="raw_symbol_entity",
            )
        )
    row = _resolved_to_row(resolved, deps.now())
    saved = deps.repos.entities.upsert(row)
    resolved = _row_to_resolved(saved)
    return {"resolved_entity": resolved, "entity_id": resolved.entity_id, "degraded": degraded}


def _row_to_resolved(row: EntityRow) -> ResolvedEntity:
    return ResolvedEntity(
        entity_id=row.id,
        node_type=row.node_type,
        name=row.name,
        aliases=row.aliases(),
        identifiers=row.identifiers(),
        market=row.market,
    )


def _resolved_to_row(entity: ResolvedEntity, now: str) -> EntityRow:
    return EntityRow(
        id=entity.entity_id,
        node_type=entity.node_type,
        name=entity.name,
        aliases_json=json.dumps(entity.aliases, sort_keys=True),
        identifiers_json=json.dumps(entity.identifiers, sort_keys=True),
        market=entity.market,
        created_at=now,
        updated_at=now,
    )


def _fallback_entity(raw_input: PositionInput) -> ResolvedEntity:
    symbol = raw_input.symbol.upper()
    market = raw_input.market.upper()
    entity_id = f"entity-{_slug(market)}-{_slug(symbol)}"
    return ResolvedEntity(
        entity_id=entity_id,
        node_type="company",
        name=raw_input.name or symbol,
        aliases=[symbol],
        identifiers={"symbol": symbol},
        market=raw_input.market,
    )


def _normalize_entity_identifiers(entity: ResolvedEntity) -> ResolvedEntity:
    identifiers = dict(entity.identifiers)
    if "symbol" not in identifiers:
        for alias in SYMBOL_ALIASES:
            value = identifiers.pop(alias, None)
            if isinstance(value, str) and value.strip():
                identifiers["symbol"] = value.strip().upper()
                break
    else:
        identifiers["symbol"] = identifiers["symbol"].strip().upper()
    return entity.model_copy(update={"identifiers": identifiers})


def _prompt(raw_input: PositionInput) -> str:
    return (
        "Resolve this investment holding into a company entity. "
        "In identifiers, use the key 'symbol' for listed tickers; do not use "
        "'ticker' or 'code'. Examples: {'symbol':'AAPL'}, {'cik':'0000320193'}, "
        "{'isin':'US0378331005'}. "
        f"symbol={raw_input.symbol}; market={raw_input.market}; name={raw_input.name or ''}"
    )


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
