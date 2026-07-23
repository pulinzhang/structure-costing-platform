"""
值解析工具模块

纯函数，无状态，易于单元测试。
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


def parse_decimal(value: Any) -> Optional[Decimal]:
    """解析数值，处理 / ~ 等特殊字符"""
    if value is None:
        return None

    val_str = str(value).strip()
    if not val_str:
        return None

    val_str = re.sub(r"[^0-9.\-/~]", "", val_str)

    if not val_str:
        return None

    if "/" in val_str:
        parts = val_str.split("/")
        try:
            val_str = str(float(parts[0]) / float(parts[1]))
        except (ValueError, ZeroDivisionError):
            pass

    if "~" in val_str:
        val_str = val_str.split("~")[0].strip()

    try:
        return Decimal(val_str)
    except (InvalidOperation, ValueError):
        return None


def parse_int(value: Any) -> Optional[int]:
    """解析整数"""
    if value is None:
        return None
    val_str = str(value).strip()
    if not val_str:
        return None
    try:
        if "." in val_str:
            return int(float(val_str))
        return int(val_str)
    except (ValueError, InvalidOperation):
        return None
