"""Sheet 处理器注册表。

根据 sheet 名字关键字路由到对应的处理器。
没有匹配的处理器 → DefaultSheetHandler。
"""

from .angang_handler import AngangSheetHandler
from .anshen_handler import AnshenSheetHandler
from .default_handler import DefaultSheetHandler
from .magang_handler import MagangSheetHandler
from .shougang_handler import ShougangSheetHandler
from .tanggang_handler import TanggangSheetHandler
from .vama_handler import VamaSheetHandler


def find_handler(sheet_name: str):
    """根据 sheet 名字找到合适的处理器。"""
    for handler_cls, keywords in _HANDLERS:
        if any(kw in sheet_name for kw in keywords):
            return handler_cls()
    return DefaultSheetHandler()


# (处理器类, 匹配关键字列表)
_HANDLERS: list[tuple[type, tuple[str, ...]]] = [
    (TanggangSheetHandler, ("唐钢",)),
    (MagangSheetHandler, ("马钢",)),
    (ShougangSheetHandler, ("首钢",)),
    (AngangSheetHandler, ("鞍钢集团", "鞍钢（")),
    (AnshenSheetHandler, ("鞍神",)),
    (VamaSheetHandler, ("VAMA", "华菱")),
]
