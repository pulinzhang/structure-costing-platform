"""布点行身份与列表筛选项是否一致。"""

from __future__ import annotations


def matches_die_identity(
    row_supplier: str | None,
    row_version: str | None,
    *,
    stamping_supplier: str | None,
    version: str | None,
) -> bool:
    """未选筛时全部匹配；选了则须与行上快照一致。"""
    return (not stamping_supplier or (row_supplier or "").strip() == stamping_supplier) and (
        not version or (row_version or "").strip() == version
    )
