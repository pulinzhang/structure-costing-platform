"""车型代号归一化：冲压工艺表与 BOM 材料清单解析后统一存储格式。"""

from __future__ import annotations

import re

# CJK 统一表意文字及扩展区（剔除中文前缀如「青岛」、后缀如「样例」）
_CJK_RE = re.compile(r"[\u2e80-\u9fff\u3400-\u4dbf\uf900-\ufaff]")


def normalize_vehicle_model(value: str | None) -> str | None:
    """
    将解析出的车型代号归一化为无中文的代号。

    例：青岛T28 → T28，T28样例 → T28，T28 → T28。
  车型代号业务上不含中文；剔除 CJK 后若为空则返回 None。
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = _CJK_RE.sub("", text).strip(" -_—/\\")
    return normalized or None
