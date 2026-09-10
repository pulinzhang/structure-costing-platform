"""权限目录：从 catalog.json 加载并缓存。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

_CATALOG_PATH = Path(__file__).with_name("catalog.json")


class PermissionAuditLabel(TypedDict):
    """权限码对应的审计文案（来自 catalog 树路径）。"""

    code: str
    op_label: str
    menu_label: str
    breadcrumb: str


class CatalogFilterOption(TypedDict):
    """操作日志筛选：菜单或操作。"""

    code: str
    label: str
    parent_code: str | None
    breadcrumb: str


def _walk_codes(nodes: list[dict[str, Any]], out: set[str]) -> None:
    for node in nodes:
        code = node.get("code")
        if code:
            out.add(str(code))
        children = node.get("children") or []
        if children:
            _walk_codes(children, out)


def _mark_mandatory(nodes: list[dict[str, Any]], mandatory: set[str]) -> list[dict[str, Any]]:
    """返回带 mandatory 标记的树副本，供授权抽屉灰显。"""
    result: list[dict[str, Any]] = []
    for node in nodes:
        item = {
            "code": node["code"],
            "label": node.get("label") or node["code"],
            "type": node.get("type") or "menu",
            "mandatory": node["code"] in mandatory,
        }
        children = node.get("children") or []
        if children:
            item["children"] = _mark_mandatory(children, mandatory)
        else:
            item["children"] = []
        result.append(item)
    return result


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    """加载并校验 catalog.json（进程内缓存）。"""
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    tree = raw.get("tree") or []
    defaults = list(raw.get("defaults") or [])
    mandatory = list(raw.get("mandatory") or [])

    all_codes: set[str] = set()
    _walk_codes(tree, all_codes)

    if not all_codes:
        raise ValueError("catalog.json tree 为空")

    unknown_defaults = [c for c in defaults if c not in all_codes]
    unknown_mandatory = [c for c in mandatory if c not in all_codes]
    if unknown_defaults:
        raise ValueError(f"catalog.json defaults 含未知 code: {unknown_defaults}")
    if unknown_mandatory:
        raise ValueError(f"catalog.json mandatory 含未知 code: {unknown_mandatory}")

    for code in mandatory:
        if code not in defaults:
            defaults.append(code)

    result = {
        "version": raw.get("version", 1),
        "tree": tree,
        "defaults": defaults,
        "mandatory": mandatory,
        "all_codes": frozenset(all_codes),
    }
    # 与 codes.Perm 双向校验（延迟 import，避免循环）
    _assert_codes_match_catalog(result["all_codes"])
    return result


def _assert_codes_match_catalog(catalog_codes: frozenset[str]) -> None:
    from app.common.permissions.codes import get_perm_code_map

    const_map = get_perm_code_map()
    const_codes = set(const_map.values())
    missing_in_catalog = sorted(const_codes - set(catalog_codes))
    missing_in_codes = sorted(set(catalog_codes) - const_codes)
    if missing_in_catalog or missing_in_codes:
        parts: list[str] = []
        if missing_in_catalog:
            parts.append(f"codes.py 有但 catalog.json 无: {missing_in_catalog}")
        if missing_in_codes:
            parts.append(f"catalog.json 有但 codes.py 无: {missing_in_codes}")
        raise ValueError("权限码不同步: " + "; ".join(parts))


def get_tree() -> list[dict[str, Any]]:
    """授权树（含 mandatory 标记）。"""
    data = load_catalog()
    return _mark_mandatory(data["tree"], set(data["mandatory"]))


def get_defaults() -> list[str]:
    return list(load_catalog()["defaults"])


def get_mandatory() -> list[str]:
    return list(load_catalog()["mandatory"])


def get_all_codes() -> list[str]:
    return list(load_catalog()["all_codes"])


def is_valid_code(code: str) -> bool:
    return code in get_all_codes()


def _index_audit_labels(nodes: list[dict[str, Any]]) -> dict[str, PermissionAuditLabel]:
    """把 catalog 树压成 op 码 → 面包屑。"""
    out: dict[str, PermissionAuditLabel] = {}

    def walk(items: list[dict[str, Any]], ancestors: list[tuple[str, str, str]]) -> None:
        for node in items:
            code = str(node.get("code") or "")
            if not code:
                continue
            label = str(node.get("label") or code)
            node_type = str(node.get("type") or "menu")
            path = [*ancestors, (code, label, node_type)]
            if node_type == "op":
                menu_label = label
                for _code, ancestor_label, ancestor_type in reversed(path[:-1]):
                    if ancestor_type == "menu":
                        menu_label = ancestor_label
                        break
                else:
                    for _code, ancestor_label, ancestor_type in path:
                        if ancestor_type == "group":
                            menu_label = ancestor_label
                            break
                out[code] = {
                    "code": code,
                    "op_label": label,
                    "menu_label": menu_label,
                    "breadcrumb": " / ".join(part[1] for part in path),
                }
            children = node.get("children") or []
            if children:
                walk(children, path)

    walk(nodes, [])
    return out


@lru_cache(maxsize=1)
def get_audit_label_map() -> dict[str, PermissionAuditLabel]:
    tree = load_catalog()["tree"]
    return _index_audit_labels(tree)


def get_audit_label(code: str) -> PermissionAuditLabel | None:
    """按权限码取菜单路径 + 操作名；未知码返回 None。"""
    return get_audit_label_map().get(code)


def list_catalog_filter_options() -> tuple[list[CatalogFilterOption], list[CatalogFilterOption]]:
    """权限树压成操作日志筛选项（菜单 + 操作）。"""
    menus: list[CatalogFilterOption] = []
    operations: list[CatalogFilterOption] = []

    def walk(items: list[dict[str, Any]], ancestors: list[tuple[str, str, str]]) -> None:
        for node in items:
            code = str(node.get("code") or "")
            if not code:
                continue
            label = str(node.get("label") or code)
            node_type = str(node.get("type") or "menu")
            path = [*ancestors, (code, label, node_type)]
            breadcrumb = " / ".join(part[1] for part in path)
            parent_area: str | None = None
            for ancestor_code, _label, ancestor_type in reversed(path[:-1]):
                if ancestor_type in {"menu", "group"}:
                    parent_area = ancestor_code
                    break
            if node_type in {"menu", "group"}:
                menus.append(
                    {
                        "code": code,
                        "label": label,
                        "parent_code": parent_area,
                        "breadcrumb": breadcrumb,
                    }
                )
            elif node_type == "op":
                operations.append(
                    {
                        "code": code,
                        "label": label,
                        "parent_code": parent_area,
                        "breadcrumb": breadcrumb,
                    }
                )
            children = node.get("children") or []
            if children:
                walk(children, path)

    walk(load_catalog()["tree"], [])
    return menus, operations


def _under_breadcrumb(item_breadcrumb: str, prefix: str) -> bool:
    return item_breadcrumb == prefix or item_breadcrumb.startswith(prefix + " / ")


def catalog_subtree_for_menu(
    menu_code: str,
    menus: list[CatalogFilterOption] | None = None,
    operations: list[CatalogFilterOption] | None = None,
) -> tuple[list[str], list[str]]:
    """某菜单及其子树：操作码 + 菜单中文名（含历史日志 module 对照）。"""
    if menus is None or operations is None:
        menus, operations = list_catalog_filter_options()
    selected = next((item for item in menus if item["code"] == menu_code), None)
    if selected is None:
        return [], []
    prefix = selected["breadcrumb"]
    op_codes = [
        item["code"] for item in operations if _under_breadcrumb(item["breadcrumb"], prefix)
    ]
    labels = [item["label"] for item in menus if _under_breadcrumb(item["breadcrumb"], prefix)]
    return op_codes, labels


def assert_codes_synced() -> None:
    """显式触发 catalog 加载与 codes.Perm 双向校验。"""
    load_catalog()
