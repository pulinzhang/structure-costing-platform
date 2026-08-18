"""权限目录：从 catalog.json 加载并缓存。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).with_name("catalog.json")


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


def get_all_codes() -> Any:
    return load_catalog()["all_codes"]


def is_valid_code(code: str) -> bool:
    return code in get_all_codes()


def assert_codes_synced() -> None:
    """显式触发 catalog 加载与 codes.Perm 双向校验。"""
    load_catalog()
