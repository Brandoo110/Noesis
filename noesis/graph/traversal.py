from collections import deque
from dataclasses import dataclass
from collections.abc import Sequence
from typing import Literal, cast
from typing import Protocol

from noesis.db.models import EntityRow, GraphEdgeRow


class EdgesReader(Protocol):
    def list_from(self, entity_id: str) -> list[GraphEdgeRow]: ...

    def list_to(self, entity_id: str) -> list[GraphEdgeRow]: ...


class EntitiesReader(Protocol):
    def get(self, id: str) -> EntityRow | None: ...


@dataclass(frozen=True)
class EntityRef:
    id: str
    name: str
    symbol: str | None


@dataclass(frozen=True)
class OverlapPosition:
    position_id: str
    symbol: str
    entity_id: str
    confidence: float


@dataclass(frozen=True)
class OverlapGroup:
    segment_id: str
    segment_name: str
    node_type: Literal["segment", "theme"]
    basis: Literal["inferred", "source_backed"]
    positions: list[OverlapPosition]


@dataclass(frozen=True)
class SharedPosition:
    position_id: str
    symbol: str | None
    entity_id: str
    confidence: float


@dataclass(frozen=True)
class SharedSupplierGroup:
    supplier_id: str
    supplier_name: str
    node_type: Literal["company"]
    basis: Literal["inferred", "source_backed"]
    positions: list[SharedPosition]


@dataclass(frozen=True)
class MatrixAxis:
    position_id: str
    symbol: str | None
    label: str


@dataclass(frozen=True)
class CorrelationCell:
    a_position_id: str
    b_position_id: str
    shared_count: int
    shared_suppliers: list[str]


@dataclass(frozen=True)
class CorrelationMatrix:
    positions: list[MatrixAxis]
    cells: list[CorrelationCell]


def relevance_path(
    entity_id: str,
    position_id: str,
    edges_repo: EdgesReader,
    *,
    max_depth: int = 3,
) -> list[str] | None:
    if entity_id == position_id:
        return [entity_id]
    queue: deque[tuple[str, list[str]]] = deque([(entity_id, [entity_id])])
    visited = {entity_id}
    while queue:
        current_id, path = queue.popleft()
        if len(path) - 1 >= max_depth:
            continue
        for edge in edges_repo.list_from(current_id):
            next_id = edge.to_entity_id
            if next_id in visited:
                continue
            next_path = [*path, next_id]
            if next_id == position_id:
                return next_path
            visited.add(next_id)
            queue.append((next_id, next_path))
    return None


def representative_stocks(
    segment_entity_id: str,
    edges_repo: EdgesReader,
    entities_repo: EntitiesReader,
    *,
    top_n: int = 5,
) -> list[EntityRef]:
    belongs_to_edges = [
        edge
        for edge in edges_repo.list_to(segment_entity_id)
        if edge.relation == "belongs_to"
    ]
    sorted_edges = sorted(
        belongs_to_edges,
        key=lambda edge: edge.confidence,
        reverse=True,
    )
    refs: list[EntityRef] = []
    for edge in sorted_edges[:top_n]:
        row = entities_repo.get(edge.from_entity_id)
        if row is None or row.node_type != "company":
            continue
        refs.append(
            EntityRef(
                id=row.id,
                name=row.name,
                symbol=row.identifiers().get("symbol"),
            )
        )
    return refs


def portfolio_overlap(
    positions_with_seed: Sequence[tuple[str, str, str]],
    edges_repo: EdgesReader,
    entities_repo: EntitiesReader,
) -> list[OverlapGroup]:
    grouped: dict[str, list[tuple[OverlapPosition, str]]] = {}
    for position_id, symbol, seed_entity_id in positions_with_seed:
        belongs_to_edges = [
            edge
            for edge in edges_repo.list_from(seed_entity_id)
            if edge.relation == "belongs_to"
        ]
        for edge in belongs_to_edges:
            grouped.setdefault(edge.to_entity_id, []).append(
                (
                    OverlapPosition(
                        position_id=position_id,
                        symbol=symbol,
                        entity_id=seed_entity_id,
                        confidence=edge.confidence,
                    ),
                    edge.basis,
                )
            )

    groups: list[OverlapGroup] = []
    for segment_id, entries in grouped.items():
        if len(entries) < 2:
            continue
        segment = entities_repo.get(segment_id)
        if segment is None or segment.node_type not in {"segment", "theme"}:
            continue
        positions = [position for position, _basis in entries]
        groups.append(
            OverlapGroup(
                segment_id=segment.id,
                segment_name=segment.name,
                node_type=cast(Literal["segment", "theme"], segment.node_type),
                basis=_overlap_basis([basis for _position, basis in entries]),
                positions=positions,
            )
        )

    return sorted(
        groups,
        key=lambda group: (
            len(group.positions),
            max(position.confidence for position in group.positions),
        ),
        reverse=True,
    )


def shared_supply_chain(
    positions_with_seed: Sequence[tuple[str, str | None, str]],
    edges_repo: EdgesReader,
    entities_repo: EntitiesReader,
) -> list[SharedSupplierGroup]:
    grouped: dict[str, list[tuple[SharedPosition, str]]] = {}
    for position_id, symbol, seed_entity_id in positions_with_seed:
        supplier_edges = [
            edge
            for edge in edges_repo.list_from(seed_entity_id)
            if edge.relation == "supplier"
        ]
        for edge in supplier_edges:
            grouped.setdefault(edge.to_entity_id, []).append(
                (
                    SharedPosition(
                        position_id=position_id,
                        symbol=symbol,
                        entity_id=seed_entity_id,
                        confidence=edge.confidence,
                    ),
                    edge.basis,
                )
            )

    groups: list[SharedSupplierGroup] = []
    for supplier_id, entries in grouped.items():
        if len(entries) < 2:
            continue
        supplier = entities_repo.get(supplier_id)
        if supplier is None or supplier.node_type != "company":
            continue
        positions = [position for position, _basis in entries]
        groups.append(
            SharedSupplierGroup(
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                node_type="company",
                basis=_overlap_basis([basis for _position, basis in entries]),
                positions=positions,
            )
        )

    return sorted(
        groups,
        key=lambda group: (
            len(group.positions),
            max(position.confidence for position in group.positions),
        ),
        reverse=True,
    )


def supply_chain_correlation(
    positions_with_seed: Sequence[tuple[str, str | None, str]],
    edges_repo: EdgesReader,
    entities_repo: EntitiesReader | None = None,
) -> CorrelationMatrix:
    axes = [
        MatrixAxis(position_id=position_id, symbol=symbol, label=symbol or position_id)
        for position_id, symbol, _seed_entity_id in positions_with_seed
    ]
    suppliers_by_position: dict[str, set[str]] = {}
    for position_id, _symbol, seed_entity_id in positions_with_seed:
        suppliers_by_position[position_id] = {
            edge.to_entity_id
            for edge in edges_repo.list_from(seed_entity_id)
            if edge.relation == "supplier"
        }

    cells: list[CorrelationCell] = []
    for left_index, left in enumerate(axes):
        for right in axes[left_index + 1 :]:
            shared = (
                suppliers_by_position.get(left.position_id, set())
                & suppliers_by_position.get(right.position_id, set())
            )
            if not shared:
                continue
            cells.append(
                CorrelationCell(
                    a_position_id=left.position_id,
                    b_position_id=right.position_id,
                    shared_count=len(shared),
                    shared_suppliers=_supplier_names(shared, entities_repo),
                )
            )
    return CorrelationMatrix(positions=axes, cells=cells)


def _supplier_names(
    supplier_ids: set[str],
    entities_repo: EntitiesReader | None,
) -> list[str]:
    names: list[str] = []
    for supplier_id in sorted(supplier_ids):
        entity = entities_repo.get(supplier_id) if entities_repo is not None else None
        names.append(entity.name if entity is not None else supplier_id)
    return names


def _overlap_basis(bases: Sequence[str]) -> Literal["inferred", "source_backed"]:
    return "inferred" if "inferred" in bases else "source_backed"
