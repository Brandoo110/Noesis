from noesis.db.models import PositionRow
from noesis.graph.state import GraphDeps


def dedupe_positions(rows: list[PositionRow], deps: GraphDeps) -> list[PositionRow]:
    selected: dict[tuple[str, str, str, str], PositionRow] = {}
    order: list[tuple[str, str, str, str]] = []
    for row in rows:
        key = position_identity(row)
        if key not in selected:
            order.append(key)
            selected[key] = row
            continue
        selected[key] = preferred_position([selected[key], row], deps)
    return [selected[key] for key in order]


def preferred_position(rows: list[PositionRow], deps: GraphDeps) -> PositionRow:
    return max(rows, key=lambda row: _position_rank(row, deps))


def position_identity(row: PositionRow) -> tuple[str, str, str, str]:
    return (
        row.user_id,
        position_label(row).casefold(),
        row.market.strip().casefold(),
        row.kind,
    )


def position_label(row: PositionRow) -> str:
    symbol = row.symbol.strip()
    if symbol:
        return symbol
    if row.name:
        return row.name
    return "unknown"


def _position_rank(row: PositionRow, deps: GraphDeps) -> tuple[int, int, int]:
    latest_run = deps.repos.runs.latest_seed_for_position(row.id)
    has_live_graph = (
        latest_run is not None
        and latest_run.status in {"running", "awaiting_confirmation", "completed"}
    )
    return (
        1 if has_live_graph else 0,
        1 if latest_run is not None else 0,
        1 if row.name else 0,
    )
