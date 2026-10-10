"""权限目录：从 catalog.json 加载并缓存。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import NotRequired, TypedDict

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


class PermissionCatalogNode(TypedDict):
    """catalog.json 里的一个节点。children 可以不写。"""

    code: str
    label: str
    type: str
    children: NotRequired[list[PermissionCatalogNode]]


class PermissionDrawerNode(TypedDict):
    """授权树节点。在目录节点上补了 mandatory。"""

    code: str
    label: str
    type: str
    mandatory: bool
    children: list[PermissionDrawerNode]


class PermissionCatalog(TypedDict):
    version: int
    tree: list[PermissionCatalogNode]
    defaults: list[str]
    mandatory: list[str]
    all_codes: frozenset[str]


def _require_str(value: object, field_name: str) -> str:
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"catalog.json 节点缺少 {field_name}")


def _parse_catalog_node(raw: object) -> PermissionCatalogNode:
    if not isinstance(raw, dict):
        raise ValueError("catalog.json 节点不是对象")
    children_raw = raw.get("children", [])
    if not isinstance(children_raw, list):
        raise ValueError("catalog.json children 不是数组")
    node: PermissionCatalogNode = {
        "code": _require_str(raw.get("code"), "code"),
        "label": _require_str(raw.get("label"), "label"),
        "type": _require_str(raw.get("type"), "type"),
    }
    if children_raw:
        node["children"] = [_parse_catalog_node(child) for child in children_raw]
    return node


def _parse_str_list(raw: object, field_name: str) -> list[str]:
    if not isinstance(raw, list):
        raise ValueError(f"catalog.json {field_name} 不是数组")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(f"catalog.json {field_name} 含非字符串")
        values.append(item)
    return values


def _walk_codes(nodes: list[PermissionCatalogNode], out: set[str]) -> None:
    for node in nodes:
        code = node.get("code")
        if code:
            out.add(str(code))
        children = node.get("children") or []
        if children:
            _walk_codes(children, out)


def _mark_mandatory(
    nodes: list[PermissionCatalogNode], mandatory: set[str]
) -> list[PermissionDrawerNode]:
    """返回带 mandatory 标记的树副本，供授权抽屉灰显。"""
    result: list[PermissionDrawerNode] = []
    for node in nodes:
        children = node.get("children") or []
        result.append(
            {
                "code": node["code"],
                "label": node.get("label") or node["code"],
                "type": node.get("type") or "menu",
                "mandatory": node["code"] in mandatory,
                "children": _mark_mandatory(children, mandatory) if children else [],
            }
        )
    return result


@lru_cache(maxsize=1)
def load_catalog() -> PermissionCatalog:
    """加载并校验 catalog.json（进程内缓存）。"""
    payload: object = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("catalog.json 不是对象")
    tree_raw = payload.get("tree") or []
    if not isinstance(tree_raw, list):
        raise ValueError("catalog.json tree 不是数组")
    tree = [_parse_catalog_node(node) for node in tree_raw]
    defaults = _parse_str_list(payload.get("defaults") or [], "defaults")
    mandatory = _parse_str_list(payload.get("mandatory") or [], "mandatory")
    version_raw = payload.get("version", 1)
    version = version_raw if isinstance(version_raw, int) else 1

    all_codes: set[str] = set()
    _walk_codes(tree, all_codes)

    if not all_codes:
        raise ValueError("catalog.json tree 为空")

    unknown_defaults = [code for code in defaults if code not in all_codes]
    unknown_mandatory = [code for code in mandatory if code not in all_codes]
    if unknown_defaults:
        raise ValueError(f"catalog.json defaults 含未知 code: {unknown_defaults}")
    if unknown_mandatory:
        raise ValueError(f"catalog.json mandatory 含未知 code: {unknown_mandatory}")

    for code in mandatory:
        if code not in defaults:
            defaults.append(code)

    result: PermissionCatalog = {
        "version": version,
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


def get_tree() -> list[PermissionDrawerNode]:
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


def _index_audit_labels(nodes: list[PermissionCatalogNode]) -> dict[str, PermissionAuditLabel]:
    """把 catalog 树压成 op 码 → 面包屑。"""
    out: dict[str, PermissionAuditLabel] = {}

    def walk(items: list[PermissionCatalogNode], ancestors: list[tuple[str, str, str]]) -> None:
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

    def walk(items: list[PermissionCatalogNode], ancestors: list[tuple[str, str, str]]) -> None:
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
