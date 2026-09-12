"""BOM 快照树：缩进、插分总成占位行。

冲压/钢价卡片字段在 stamping.py。
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bom.node import BomNode
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.repositories.bom.bom_repository import BomNodeRepository
from app.schemas.vo.assembly_cost_restore_vo import RestoreExceptionVO, RestoreMaterialNodeVO
from app.services.costing.assembly_cost.codes import card_short_code
from app.services.costing.assembly_cost.restore.labels import cost_source_label
from app.services.costing.assembly_cost.restore.money import _money


class RestoreTree:
    def __init__(self, node_repo: BomNodeRepository) -> None:
        self.node_repo = node_repo

    def _snapshot_parents(
        self,
        db: Session,
        card: AssemblyCost,
        exceptions: list[RestoreExceptionVO],
    ) -> tuple[bool, dict[int, int | None], list[BomNode]]:
        empty: list[BomNode] = []
        if card.bom_snapshot_id is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="identity",
                    message="当时的材料清单找不到了",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
            return False, {}, empty
        nodes = self.node_repo.list_by_snapshot(db, card.bom_snapshot_id)
        if not nodes:
            exceptions.append(
                RestoreExceptionVO(
                    kind="identity",
                    message="当时的材料清单找不到了",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
            return False, {}, empty
        by_id = {node.id: node for node in nodes}
        parent_map = {node.id: node.parent_id for node in nodes}
        if card.source_node_id not in by_id:
            exceptions.append(
                RestoreExceptionVO(
                    kind="identity",
                    message="材料清单改过了，要重新算价",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
            return False, parent_map, nodes
        return True, parent_map, nodes

    def _indent_level(
        self,
        item: AssemblyCostItem,
        *,
        tree_from_snapshot: bool,
        parent_by_id: dict[int, int | None],
    ) -> int:
        if not tree_from_snapshot or item.bom_node_id is None:
            return int(item.node_level or 0)
        depth = 0
        node_id: int | None = item.bom_node_id
        seen: set[int] = set()
        while node_id is not None and node_id in parent_by_id and node_id not in seen:
            seen.add(node_id)
            node_id = parent_by_id.get(node_id)
            depth += 1
            if depth > 40:
                break
        return max(0, depth - 1) if depth else int(item.node_level or 0)

    def _indent_from_card(
        self,
        node_id: int | None,
        card_source_id: int,
        parent_by_id: dict[int, int | None],
    ) -> int:
        if node_id is None:
            return 0
        depth = 0
        current: int | None = node_id
        seen: set[int] = set()
        while current is not None and current != card_source_id:
            if current in seen:
                break
            seen.add(current)
            current = parent_by_id.get(current)
            depth += 1
            if depth > 40:
                break
        return max(0, depth - 1)

    def _weave_sub_assemblies(
        self,
        *,
        card: AssemblyCost,
        item_nodes: list[RestoreMaterialNodeVO],
        snapshot_nodes: list[BomNode],
        parent_by_id: dict[int, int | None],
        view: str,
    ) -> list[RestoreMaterialNodeVO]:
        children_by_parent: dict[int | None, list[BomNode]] = defaultdict(list)
        for snap in snapshot_nodes:
            children_by_parent[snap.parent_id].append(snap)
        for siblings in children_by_parent.values():
            siblings.sort(key=lambda row: (row.sort_no, row.id))
        by_bom_id = {node.bom_node_id: node for node in item_nodes if node.bom_node_id is not None}
        root_node = next((row for row in snapshot_nodes if row.id == card.source_node_id), None)
        root_seq = ""
        if root_node is not None and root_node.seq_no is not None:
            root_seq = str(root_node.seq_no)
        ordered: list[RestoreMaterialNodeVO] = []
        used: set[int] = set()
        sort_no = 0

        def emit(node: RestoreMaterialNodeVO, bom_id: int, seq_label: str) -> None:
            nonlocal sort_no
            sort_no += 1
            indent = self._indent_from_card(bom_id, card.source_node_id, parent_by_id)
            ordered.append(
                node.model_copy(
                    update={"sort_no": sort_no, "indent_level": indent, "seq_label": seq_label}
                )
            )
            used.add(bom_id)

        def walk(parent_id: int, path_qty: Decimal, parent_seq: str) -> None:
            nonlocal sort_no
            for index, child in enumerate(children_by_parent.get(parent_id, []), start=1):
                child_qty = path_qty * (
                    Decimal(str(child.qty)) if child.qty is not None else Decimal("1")
                )
                seq_label = f"{parent_seq}-{index}" if parent_seq else str(index)
                kids = children_by_parent.get(child.id, [])
                if child.id in by_bom_id:
                    emit(by_bom_id[child.id], child.id, seq_label)
                elif kids:
                    sort_no += 1
                    ordered.append(
                        self._sub_assembly_node(
                            card=card,
                            bom_node=child,
                            path_qty=child_qty,
                            sort_no=sort_no,
                            seq_label=seq_label,
                            item_nodes=item_nodes,
                            parent_by_id=parent_by_id,
                            view=view,
                        )
                    )
                    used.add(child.id)
                if kids:
                    walk(child.id, child_qty, seq_label)

        walk(card.source_node_id, Decimal("1"), root_seq)
        for leftover in item_nodes:
            if leftover.bom_node_id is None or leftover.bom_node_id not in used:
                sort_no += 1
                ordered.append(leftover.model_copy(update={"sort_no": sort_no}))
        return ordered

    def _sub_assembly_node(
        self,
        *,
        card: AssemblyCost,
        bom_node: BomNode,
        path_qty: Decimal,
        sort_no: int,
        seq_label: str,
        item_nodes: list[RestoreMaterialNodeVO],
        parent_by_id: dict[int, int | None],
        view: str,
    ) -> RestoreMaterialNodeVO:
        indent = self._indent_from_card(bom_node.id, card.source_node_id, parent_by_id)
        counted = {"stamping", "annual", "bundle"}
        material_amt = _money(
            sum(
                (
                    node.line_amount
                    for node in item_nodes
                    if node.bom_node_id
                    and node.cost_source in counted
                    and self._is_bom_descendant(node.bom_node_id, bom_node.id, parent_by_id)
                ),
                Decimal("0"),
            )
        )
        line = material_amt
        unit = _money(material_amt / path_qty) if path_qty else Decimal("0")
        return RestoreMaterialNodeVO(
            sort_no=sort_no,
            indent_level=indent,
            node_level=int(bom_node.level or 0),
            bom_node_id=bom_node.id,
            part_number=bom_node.part_number,
            part_name=bom_node.part_name,
            short_code=card_short_code(
                part_number=bom_node.part_number,
                level=bom_node.level,
                view=view,
            ),
            seq_label=seq_label,
            node_role=bom_node.node_role,
            supply_type=None,
            cost_source="sub_assembly",
            cost_source_label=cost_source_label("sub_assembly"),
            unit_price=unit,
            effective_qty=path_qty,
            line_amount=line,
        )

    def _is_bom_descendant(
        self,
        node_id: int,
        ancestor_id: int,
        parent_by_id: dict[int, int | None],
    ) -> bool:
        current: int | None = node_id
        seen: set[int] = set()
        while current is not None:
            if current == ancestor_id:
                return True
            if current in seen:
                return False
            seen.add(current)
            current = parent_by_id.get(current)
        return False
