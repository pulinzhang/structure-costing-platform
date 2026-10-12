"""焊接工艺拆解过程文案（给人看，不写字段名）。"""

from __future__ import annotations


def format_scope(
    location: str,
    vehicle_model: str,
    bom_version: str,
    customer_name: str | None,
) -> str:
    line = f"这次拆的是：{location}，{vehicle_model}，版本 {bom_version}"
    customer = (customer_name or "").strip()
    if customer:
        line += f"，顾客 {customer}"
    return f"{line}。"


def format_bom_scope(node_count: int, weld_count: int) -> str:
    return f"材料清单一共 {node_count} 行，其中 {weld_count} 行写了焊接信息，会拆成工艺。"


def format_leaf_without_weld(count: int) -> str | None:
    if count <= 0:
        return None
    return (
        f"另外有 {count} 个总成下面没有零件，材料清单上也没写焊接信息，这次不拆。"
        "如果这些件要计焊接费，请先在材料清单补上焊接信息，再重新拆。"
    )


def format_cleared(deleted: int) -> str:
    if deleted <= 0:
        return "没有上次没审核的拆解，不用清。"
    return f"已清掉上次没审核的拆解 {deleted} 个零件，按这次材料清单重新拆。"


def format_finished(node_count: int, line_count: int) -> str:
    return f"拆完了：{node_count} 个零件，{line_count} 条焊接工艺。"
