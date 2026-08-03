"""Sheet 处理器注册表。

根据 sheet 名字关键字路由到对应的处理器。
没有匹配的处理器 → DefaultSheetHandler。
"""

from .angang_handler import AngangSheetHandler
from .anshen_handler import AnshenSheetHandler
from .default_handler import DefaultSheetHandler
from .magang_handler import MagangSheetHandler
from .magang_new_handler import MagangNewSheetHandler
from .shougang_handler import ShougangSheetHandler
from .tanggang_handler import TanggangSheetHandler
from .vama_handler import VamaSheetHandler


def find_handler(sheet_name: str):
    """根据 sheet 名字找到合适的处理器（大小写不敏感）。"""
    sheet_lower = sheet_name.lower()
    for handler_cls, keywords in _HANDLERS:
        if any(kw.lower() in sheet_lower for kw in keywords):
            return handler_cls()
    return DefaultSheetHandler()


# (处理器类, 匹配关键字列表)
_HANDLERS: list[tuple[type, tuple[str, ...]]] = [
    # 唐钢：冷轧/镀锌按钢种+宽度分段加价，厚度分档独立处理
    (TanggangSheetHandler, ("唐钢",)),
    # 马钢（新的独立 handler，与首钢布局一致，sheet 名"马钢"）
    (MagangSheetHandler, ("马钢",)),
    # 马钢（旧版，按钢种（DC01等）区分宽度加价，钢种列表在表格列头）
    (MagangNewSheetHandler, ("马钢(新)",)),
    # 首钢：冷轧按厚度+宽度组合，镀锌按厚度+宽度组合
    (ShougangSheetHandler, ("首钢",)),
    # 鞍钢/鞍本/本钢：按宽度区间设固定价差，冷/镀/酸洗各一套
    (AngangSheetHandler, ("鞍钢集团","鞍本","本钢", "鞍钢（")),
    # 鞍神：按厚度区间（2.0~0.75mm）与宽度（750~1250mm）组合
    (AnshenSheetHandler, ("鞍神",)),
    # VAMA/华菱：按钢种+厚度+宽度三维组合加价
    (VamaSheetHandler, ("Vama", "华菱")),
]
