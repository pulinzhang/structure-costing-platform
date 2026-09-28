"""采购对象列表分类（纯函数，不写库）。

只根据一版 `bom_nodes` 树判定列入集合与检测结论。
退化供货件仅 L0：无子件，或全部一级件都没有内部号。
L1 有内部号才列入采购对象；无内部号进核对区（标准件/胶等），例如点焊胶、焊接螺柱组合件。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from app.common.bom.manufacturing_category import resolve_manufacturing_category
from app.models.bom.node import BomNode

SECTION_OBJECT = "object"
SECTION_OTHER_LEAF = "other_leaf"
SECTION_ANOMALY = "anomaly"

KIND_L0_DEGENERATE = "l0_degenerate"
KIND_L1_SUBASSEMBLY = "l1_subassembly"
KIND_L1_STAMPING = "l1_stamping"

SUBTYPE_SPECIAL_PROCESS = "special_process"
SUBTYPE_STAMPING_BLANK = "stamping_blank"

OUTSOURCE_REMARK_KEYS = (
    "凸焊总成供货",
    "总成供货",
    "冲压单件供货",
    "单件供货",
    "黑漆件供货",
    "电泳",
)

SPECIAL_PROCESS_KEYS = ("电泳", "面积", "黑漆", "喷粉", "电镀")

STAMPING_LOOKALIKE_NAME_KEYS = ("支架", "加强板")


@dataclass(slots=True)
class ClassifiedRow:
    """分类结果一行（尚未落库）。"""

    source_node_id: int
    section: str
    object_kind: str | None
    degenerate_subtype: str | None
    part_number: str
    part_name: str | None
    internal_number: str | None
    level: int
    node_role: str
    qty: Decimal | None
    qty_unit: str
    l0_part_number: str
    l0_part_name: str | None
    parent_part_number: str | None
    parent_part_name: str | None
    excel_filename: str | None
    excel_sheet_name: str | None
    excel_row: int | None
    child_count: int
    weld_info: str | None
    remark: str | None
    has_outsource_remark: bool
    material: str | None
    thickness_text: str | None
    material_mill: str | None
    data_gap: str | None
    alert_code: str | None


@dataclass(slots=True)
class ClassifyCounts:
    l0_count: int = 0
    l0_with_children_count: int = 0
    l2_count: int = 0
    subassembly_child_sum: int = 0
    object_l0_degenerate_count: int = 0
    object_l0_special_process_count: int = 0
    object_l0_stamping_blank_count: int = 0
    object_l1_subassembly_count: int = 0
    object_l1_stamping_count: int = 0
    other_leaf_count: int = 0
    anomaly_count: int = 0


@dataclass(slots=True)
class ClassifyResult:
    rows: list[ClassifiedRow] = field(default_factory=list)
    counts: ClassifyCounts = field(default_factory=ClassifyCounts)
    qa_passed: bool = True
    qa_error_text: str | None = None


def _text(value: str | None) -> str:
    return (value or "").strip()


def _has_any_key(haystack: str, keys: tuple[str, ...]) -> bool:
    return any(key in haystack for key in keys)


def _has_outsource_remark(node: BomNode) -> bool:
    return _has_any_key(_text(node.remark), OUTSOURCE_REMARK_KEYS)


def _degenerate_subtype(node: BomNode) -> str:
    blob = f"{_text(node.weld_info)}{_text(node.remark)}"
    if _has_any_key(blob, SPECIAL_PROCESS_KEYS):
        return SUBTYPE_SPECIAL_PROCESS
    return SUBTYPE_STAMPING_BLANK


def _lacks_internal_number(node: BomNode) -> bool:
    return not _text(getattr(node, "internal_number", None))


def _is_l1_stamping_leaf(node: BomNode) -> bool:
    """L1 叶子冲压件：make → 料厚 → 制造类别。禁止把 L0 supply 送进本函数。"""
    role = _text(node.node_role).lower()
    if role == "make":
        return True
    if node.thickness_mm is not None:
        return True
    category = resolve_manufacturing_category(
        node_role=node.node_role,
        is_supply_unit=False,
        has_children=False,
        part_name=node.part_name,
        material=node.material,
        part_number=node.part_number,
        thickness_mm=node.thickness_mm,
        qty_unit=node.qty_unit,
    )
    return category == "stamping"


def _join_alerts(*codes: str | None) -> str | None:
    parts = [code for code in codes if code]
    if not parts:
        return None
    return ",".join(parts)


def classify_nodes(nodes: Sequence[BomNode]) -> ClassifyResult:
    """对一版材料清单节点做列入分类 + 7.1–7.3 检测。"""
    by_id: dict[int, BomNode] = {node.id: node for node in nodes}
    children_map: dict[int | None, list[BomNode]] = defaultdict(list)
    for node in nodes:
        children_map[node.parent_id].append(node)

    def child_count_of(node_id: int) -> int:
        return len(children_map.get(node_id, []))

    def resolve_l0(node: BomNode) -> BomNode:
        current = node
        while current.parent_id is not None:
            parent = by_id.get(current.parent_id)
            if parent is None:
                break
            current = parent
        return current

    def parent_of(node: BomNode) -> BomNode | None:
        if node.parent_id is None:
            return None
        return by_id.get(node.parent_id)

    def l1_children_of(node_id: int) -> list[BomNode]:
        return [child for child in children_map.get(node_id, []) if int(child.level) == 1]

    def is_degenerate_l0(node: BomNode) -> bool:
        """仅 L0。无子件一定退化；全部 L1 都没有内部号也退化。不看 L2。"""
        children = children_map.get(node.id, [])
        if not children:
            return True
        return all(_lacks_internal_number(child) for child in l1_children_of(node.id))

    l0_nodes = [n for n in nodes if int(n.level) == 0]
    l1_nodes = [n for n in nodes if int(n.level) == 1]
    l2_nodes = [n for n in nodes if int(n.level) == 2]
    l0_with_children = [n for n in l0_nodes if child_count_of(n.id) > 0]
    l0_degenerate_nodes = [n for n in l0_nodes if is_degenerate_l0(n)]
    degenerate_l0_ids = {n.id for n in l0_degenerate_nodes}
    l0_structured = [n for n in l0_nodes if n.id not in degenerate_l0_ids]

    def belongs_to_degenerate_l0(node: BomNode) -> bool:
        return resolve_l0(node).id in degenerate_l0_ids

    l1_under_structured = [n for n in l1_nodes if not belongs_to_degenerate_l0(n)]
    l1_object_subassemblies = [
        n for n in l1_under_structured if child_count_of(n.id) > 0 and not _lacks_internal_number(n)
    ]
    l1_leaves = [n for n in l1_under_structured if child_count_of(n.id) == 0]
    l1_non_object = [
        n for n in l1_under_structured if child_count_of(n.id) > 0 and _lacks_internal_number(n)
    ]

    rows: list[ClassifiedRow] = []

    def make_row(
        node: BomNode,
        *,
        section: str,
        object_kind: str | None,
        degenerate_subtype: str | None,
        data_gap: str | None,
        alert_code: str | None,
    ) -> ClassifiedRow:
        parent = parent_of(node)
        l0 = node if int(node.level) == 0 else resolve_l0(node)
        excel_missing = (not _text(node.excel_filename)) or (node.excel_row is None)
        return ClassifiedRow(
            source_node_id=node.id,
            section=section,
            object_kind=object_kind,
            degenerate_subtype=degenerate_subtype,
            part_number=node.part_number,
            part_name=node.part_name,
            internal_number=node.internal_number,
            level=int(node.level),
            node_role=node.node_role,
            qty=node.qty,
            qty_unit=node.qty_unit or "pcs",
            l0_part_number=l0.part_number,
            l0_part_name=l0.part_name,
            parent_part_number=parent.part_number if parent else None,
            parent_part_name=parent.part_name if parent else None,
            excel_filename=node.excel_filename,
            excel_sheet_name=node.excel_sheet_name,
            excel_row=node.excel_row,
            child_count=child_count_of(node.id),
            weld_info=node.weld_info,
            remark=node.remark,
            has_outsource_remark=_has_outsource_remark(node),
            material=node.material,
            thickness_text=node.thickness_text,
            material_mill=node.material_mill,
            data_gap=data_gap,
            alert_code=_join_alerts(
                alert_code,
                "excel_trace_missing" if excel_missing else None,
            ),
        )

    for node in l0_degenerate_nodes:
        material_empty = not (
            _text(node.material) or _text(node.thickness_text) or _text(node.material_mill)
        )
        rows.append(
            make_row(
                node,
                section=SECTION_OBJECT,
                object_kind=KIND_L0_DEGENERATE,
                degenerate_subtype=_degenerate_subtype(node),
                data_gap="l0_material_missing" if material_empty else None,
                alert_code="l0_material_missing" if material_empty else None,
            )
        )

    for node in l1_object_subassemblies:
        weld_empty = not _text(node.weld_info)
        rows.append(
            make_row(
                node,
                section=SECTION_OBJECT,
                object_kind=KIND_L1_SUBASSEMBLY,
                degenerate_subtype=None,
                data_gap=None,
                alert_code="subassembly_no_weld" if weld_empty else None,
            )
        )

    for node in l1_non_object:
        rows.append(
            make_row(
                node,
                section=SECTION_OTHER_LEAF,
                object_kind=None,
                degenerate_subtype=None,
                data_gap=None,
                alert_code=None,
            )
        )

    for node in l1_leaves:
        if _lacks_internal_number(node):
            name = _text(node.part_name)
            looks_stamping = node.thickness_mm is not None and _has_any_key(
                name, STAMPING_LOOKALIKE_NAME_KEYS
            )
            rows.append(
                make_row(
                    node,
                    section=SECTION_OTHER_LEAF,
                    object_kind=None,
                    degenerate_subtype=None,
                    data_gap=None,
                    alert_code="other_leaf_looks_stamping" if looks_stamping else None,
                )
            )
            continue
        if _is_l1_stamping_leaf(node):
            weld_present = bool(_text(node.weld_info))
            rows.append(
                make_row(
                    node,
                    section=SECTION_OBJECT,
                    object_kind=KIND_L1_STAMPING,
                    degenerate_subtype=None,
                    data_gap=None,
                    alert_code="stamping_has_weld" if weld_present else None,
                )
            )
            continue
        name = _text(node.part_name)
        looks_stamping = node.thickness_mm is not None and _has_any_key(
            name, STAMPING_LOOKALIKE_NAME_KEYS
        )
        rows.append(
            make_row(
                node,
                section=SECTION_OTHER_LEAF,
                object_kind=None,
                degenerate_subtype=None,
                data_gap=None,
                alert_code="other_leaf_looks_stamping" if looks_stamping else None,
            )
        )

    for node in l0_structured:
        if not _has_outsource_remark(node):
            continue
        rows.append(
            make_row(
                node,
                section=SECTION_ANOMALY,
                object_kind=None,
                degenerate_subtype=None,
                data_gap=None,
                alert_code="l0_outsource_remark",
            )
        )

    counts = ClassifyCounts(
        l0_count=len(l0_nodes),
        l0_with_children_count=len(l0_with_children),
        l2_count=len(l2_nodes),
        subassembly_child_sum=sum(child_count_of(n.id) for n in l1_object_subassemblies),
        object_l0_degenerate_count=sum(1 for r in rows if r.object_kind == KIND_L0_DEGENERATE),
        object_l0_special_process_count=sum(
            1
            for r in rows
            if r.object_kind == KIND_L0_DEGENERATE
            and r.degenerate_subtype == SUBTYPE_SPECIAL_PROCESS
        ),
        object_l0_stamping_blank_count=sum(
            1
            for r in rows
            if r.object_kind == KIND_L0_DEGENERATE
            and r.degenerate_subtype == SUBTYPE_STAMPING_BLANK
        ),
        object_l1_subassembly_count=sum(1 for r in rows if r.object_kind == KIND_L1_SUBASSEMBLY),
        object_l1_stamping_count=sum(1 for r in rows if r.object_kind == KIND_L1_STAMPING),
        other_leaf_count=sum(1 for r in rows if r.section == SECTION_OTHER_LEAF),
        anomaly_count=sum(1 for r in rows if r.section == SECTION_ANOMALY),
    )

    qa_errors: list[str] = []
    if counts.object_l0_degenerate_count != len(l0_degenerate_nodes):
        qa_errors.append(
            "完备失败：无子件或全部 L1 无内部号的 L0 "
            f"{len(l0_degenerate_nodes)} ≠ 退化供货件 {counts.object_l0_degenerate_count}"
        )
    missing_subtype = sum(
        1
        for row in rows
        if row.object_kind == KIND_L0_DEGENERATE
        and row.degenerate_subtype not in (SUBTYPE_SPECIAL_PROCESS, SUBTYPE_STAMPING_BLANK)
    )
    if missing_subtype:
        qa_errors.append(f"完备失败：{missing_subtype} 条退化供货件缺少亚类")
    subtype_sum = counts.object_l0_special_process_count + counts.object_l0_stamping_blank_count
    if subtype_sum != counts.object_l0_degenerate_count:
        qa_errors.append(
            f"完备失败：退化供货件 {counts.object_l0_degenerate_count} ≠ "
            f"特殊工艺 {counts.object_l0_special_process_count} + "
            f"冲压毛坯 {counts.object_l0_stamping_blank_count}"
        )
    if counts.object_l1_subassembly_count != len(l1_object_subassemblies):
        qa_errors.append(
            "完备失败：带内部号的 L1 有子件 "
            f"{len(l1_object_subassemblies)} ≠ 分总成采购对象 {counts.object_l1_subassembly_count}"
        )
    leaf_classified = counts.object_l1_stamping_count + sum(
        1
        for row in rows
        if row.section == SECTION_OTHER_LEAF and row.level == 1 and row.child_count == 0
    )
    if leaf_classified != len(l1_leaves):
        qa_errors.append(
            f"完备失败：结构化总成下 L1 叶子 {len(l1_leaves)} ≠ 冲压件+核对区叶子 {leaf_classified}"
        )
    object_l1_without_internal = [
        row
        for row in rows
        if row.section == SECTION_OBJECT and row.level == 1 and not _text(row.internal_number)
    ]
    if object_l1_without_internal:
        qa_errors.append("互斥失败：无内部号的 L1 出现在采购对象区")

    seen_ids: set[int] = set()
    for row in rows:
        if row.source_node_id in seen_ids:
            qa_errors.append(f"互斥失败：source_node_id={row.source_node_id} 重复")
        seen_ids.add(row.source_node_id)

    object_structured_l0 = [
        r
        for r in rows
        if r.section == SECTION_OBJECT
        and r.level == 0
        and r.source_node_id not in degenerate_l0_ids
    ]
    if object_structured_l0:
        qa_errors.append("互斥失败：子件带内部号的供货总成出现在采购对象区")
    object_l2 = [r for r in rows if r.section == SECTION_OBJECT and r.level == 2]
    if object_l2:
        qa_errors.append("互斥失败：L2 出现在采购对象区")

    for row in rows:
        if row.object_kind == KIND_L1_SUBASSEMBLY:
            if row.child_count < 1:
                qa_errors.append(f"结构失败：分总成 {row.part_number} 无子件")
            children = children_map.get(row.source_node_id, [])
            if any(int(child.level) != 2 for child in children):
                qa_errors.append(f"结构失败：分总成 {row.part_number} 存在非 L2 子件")
        if row.object_kind == KIND_L1_STAMPING and row.child_count != 0:
            qa_errors.append(f"结构失败：{row.part_number} 应为无子件")
        if row.object_kind == KIND_L0_DEGENERATE and any(
            not _lacks_internal_number(child) for child in l1_children_of(row.source_node_id)
        ):
            qa_errors.append(f"结构失败：退化供货件 {row.part_number} 存在带内部号的一级件")
        if row.section == SECTION_OBJECT and row.level == 1:
            source = by_id.get(row.source_node_id)
            parent_id = source.parent_id if source is not None else None
            parent = by_id.get(parent_id) if parent_id is not None else None
            if parent is None or int(parent.level) != 0 or parent.id in degenerate_l0_ids:
                qa_errors.append(
                    f"结构失败：L1 采购对象 {row.part_number} 父节点不是带内部号一级件的供货总成"
                )
        if not _text(row.l0_part_number):
            qa_errors.append(f"结构失败：行 {row.part_number} 缺少供货总成零件号")

    qa_passed = not qa_errors
    return ClassifyResult(
        rows=rows,
        counts=counts,
        qa_passed=qa_passed,
        qa_error_text="\n".join(qa_errors) if qa_errors else None,
    )
