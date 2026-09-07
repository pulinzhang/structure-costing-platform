"""项目代号归一化：冲压工艺表与 BOM 材料清单解析后统一存储格式。"""

from __future__ import annotations

import re

# CJK 统一表意文字及扩展区（剔除中文前缀如「青岛」、后缀如「样例」）
_CJK_RE = re.compile(r"[\u2e80-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
# 文件名序号 ①–⑳（不含业务代号）
_ENCLOSED_NUM_RE = re.compile(r"[\u2460-\u2473]")


def normalize_vehicle_model(value: str | None) -> str | None:
    """去 CJK / 圈号后转大写。青岛T28 → T28，青岛t13j → T13J，②T13J → T13J。空则 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = _CJK_RE.sub("", text)
    normalized = _ENCLOSED_NUM_RE.sub("", normalized).strip(" -_—/\\")
    if not normalized:
        return None
    return normalized.upper()
