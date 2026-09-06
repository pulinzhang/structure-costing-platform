"""
值解析工具模块

纯函数，无状态，易于单元测试。
"""

import contextlib
import re
from decimal import Decimal, InvalidOperation
from typing import Any


def parse_decimal(value: Any) -> Decimal | None:
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
        with contextlib.suppress(ValueError, ZeroDivisionError):
            val_str = str(float(parts[0]) / float(parts[1]))

    if "~" in val_str:
        val_str = val_str.split("~")[0].strip()

    try:
        return Decimal(val_str)
    except (InvalidOperation, ValueError):
        return None


def parse_int(value: Any) -> int | None:
    """解析整数，处理带字母后缀的格式如 600T"""
    if value is None:
        return None
    val_str = str(value).strip()
    if not val_str:
        return None

    # 提取数字部分（处理 "600T"、"800t"、"1000T" 等带字母后缀的情况）
    # 保留小数点前的部分
    match = re.match(r"(\d+(?:\.\d+)?)", val_str)
    if match:
        val_str = match.group(1)
    else:
        return None

    try:
        if "." in val_str:
            return int(float(val_str))
        return int(val_str)
    except (ValueError, InvalidOperation):
        return None
