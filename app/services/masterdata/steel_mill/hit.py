"""对外解析结果。调用方拿 id 落库，拿缩写显示，拿全称写入规范列。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SteelMillHit:
    id: int
    abbreviation: str
    full_name: str
    is_enabled: bool
