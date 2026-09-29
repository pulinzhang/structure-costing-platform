"""钢厂空库种子。缩写与全称相同；别名盖住历史表头。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SteelMillSeed:
    abbreviation: str
    full_name: str
    aliases: tuple[str, ...] = ()


STEEL_MILL_SEEDS: tuple[SteelMillSeed, ...] = (
    SteelMillSeed("VAMA", "VAMA"),
    SteelMillSeed("包钢", "包钢", ("包钢(新)",)),
    SteelMillSeed("唐钢", "唐钢", ("唐钢(新)",)),
    SteelMillSeed("宝钢", "宝钢", ("宝钢(新)",)),
    SteelMillSeed("山钢", "山钢", ("山钢(新)",)),
    SteelMillSeed("本钢", "本钢"),
    SteelMillSeed("涟钢", "涟钢", ("涟钢(新)",)),
    SteelMillSeed("邯钢", "邯钢", ("邯钢(新)",)),
    SteelMillSeed("首钢", "首钢", ("首钢最新",)),
    SteelMillSeed("马钢", "马钢", ("马钢(新)",)),
    SteelMillSeed("鞍本", "鞍本", ("鞍钢集团", "TAGAL")),
    SteelMillSeed("鞍神", "鞍神"),
)
