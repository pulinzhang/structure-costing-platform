"""
焊接标准工艺名称（与 bom_welding_unit_price.item_name 对齐）

先用枚举写死，供焊接工艺拆解明细落库；未来核算按此名匹配单价。
"""

from __future__ import annotations

from enum import StrEnum

from app.common.bom.welding_billing_qty import normalize_unit_key


class WeldingStandardProcessName(StrEnum):
    """焊接单价目录中的标准工艺名称。"""

    SPOT_WELD = "焊点"
    STUD_PROJECTION_WELD = "植/螺柱/凸焊"
    RIVET = "铆接"
    CO2_WELD_SEAM = "CO2焊缝"
    HEMMING_SPOT_GLUE = "折边/点焊胶"
    ELECTROPLATING = "电镀"
    E_COAT_LE_244H = "电泳（盐雾试验要求≤244H）"
    E_COAT_244H_720H = "电泳（盐雾试验要求244H-720H）"
    E_COAT_GT_720H = "电泳（盐雾试验要求＞720H）"
    PRESS_RIVET = "压铆"
    DRIVE_RIVET = "打铆钉"
    QR_CODE = "二维码"
    BAGGING = "套袋"


# 拆解原文 token → 标准工艺名（可空表示尚不能唯一确定）
TOKEN_TO_STANDARD_PROCESS: dict[str, WeldingStandardProcessName | None] = {
    "焊点": WeldingStandardProcessName.SPOT_WELD,
    "凸焊": WeldingStandardProcessName.STUD_PROJECTION_WELD,
    "植焊": WeldingStandardProcessName.STUD_PROJECTION_WELD,
    "铆接": WeldingStandardProcessName.RIVET,
    "焊缝": WeldingStandardProcessName.CO2_WELD_SEAM,
    "弧焊": WeldingStandardProcessName.CO2_WELD_SEAM,
    "塞焊": WeldingStandardProcessName.CO2_WELD_SEAM,
    "涂胶": WeldingStandardProcessName.HEMMING_SPOT_GLUE,
    # 面积类一律按电泳（默认 ≤244H；其它盐雾档可人工改）
    "面积": WeldingStandardProcessName.E_COAT_LE_244H,
    "电泳面积": WeldingStandardProcessName.E_COAT_LE_244H,
}

# 标准工艺 → 焊接单价目录单位（与导入模板一致，供核对过程量单位）
STANDARD_PROCESS_UNIT: dict[str, str] = {
    WeldingStandardProcessName.SPOT_WELD.value: "个",
    WeldingStandardProcessName.STUD_PROJECTION_WELD.value: "个",
    WeldingStandardProcessName.RIVET.value: "个",
    WeldingStandardProcessName.CO2_WELD_SEAM.value: "CM",
    WeldingStandardProcessName.HEMMING_SPOT_GLUE.value: "MM",
    WeldingStandardProcessName.ELECTROPLATING.value: "平方",
    WeldingStandardProcessName.E_COAT_LE_244H.value: "平方",
    WeldingStandardProcessName.E_COAT_244H_720H.value: "平方",
    WeldingStandardProcessName.E_COAT_GT_720H.value: "平方",
    WeldingStandardProcessName.PRESS_RIVET.value: "个",
    WeldingStandardProcessName.DRIVE_RIVET.value: "个",
    WeldingStandardProcessName.QR_CODE.value: "个",
    WeldingStandardProcessName.BAGGING.value: "个",
}


def resolve_standard_process_name(
    process_token: str,
    *,
    tags: tuple[str, ...] = (),
) -> tuple[str | None, str]:
    """
    解析标准工艺名与映射状态。

    返回 (standard_process_name, map_status)：
      ready / ambiguous / unmapped

    业务约定：原文工艺为「面积」「电泳面积」时，一律对应标准工艺电泳
    （默认「电泳（盐雾试验要求≤244H）」），不再按电镀处理。
    ``tags`` 保留兼容调用方，面积类映射不再依赖 tags。
    """
    if process_token in ("面积", "电泳面积"):
        return WeldingStandardProcessName.E_COAT_LE_244H.value, "ready"

    standard = TOKEN_TO_STANDARD_PROCESS.get(process_token)
    if standard is None and process_token not in TOKEN_TO_STANDARD_PROCESS:
        return None, "unmapped"
    if standard is None:
        return None, "ambiguous"
    return standard.value, "ready"


def all_standard_process_names() -> list[str]:
    return [item.value for item in WeldingStandardProcessName]


_STANDARD_PROCESS_NAME_SET: frozenset[str] = frozenset(all_standard_process_names())


def list_welding_standard_catalog() -> list[tuple[str, str]]:
    """标准工艺目录：(名称, 单位)，顺序与枚举一致。"""
    return [
        (name, STANDARD_PROCESS_UNIT[name])
        for name in all_standard_process_names()
        if name in STANDARD_PROCESS_UNIT
    ]


def is_standard_process_name(name: str | None) -> bool:
    """名称是否属于焊接标准工艺目录。"""
    if not name:
        return False
    return name.strip() in _STANDARD_PROCESS_NAME_SET


def resolve_standard_process_unit(standard_process_name: str | None) -> str | None:
    """按标准工艺名取目录单位；未知或未映射时返回 None。"""
    if not standard_process_name:
        return None
    return STANDARD_PROCESS_UNIT.get(standard_process_name)


def validate_welding_unit_price_catalog(
    item_name: str,
    unit: str | None = None,
) -> None:
    """
    焊接单价门禁：名称必须属于标准工艺目录；若传入单位则须与目录单位一致。

    不一致时抛 ``ValueError``（供导入 / DTO / 手工创建复用）。
    """
    name = (item_name or "").strip()
    if not name:
        raise ValueError("名称为空，不属于焊接标准工艺目录")
    if name not in _STANDARD_PROCESS_NAME_SET:
        raise ValueError(
            f"「{name}」不属于焊接标准工艺目录"
            f"（须与拆解标准工艺名完全一致，例如「折边/点焊胶」）"
        )
    if unit is None:
        return
    expected = STANDARD_PROCESS_UNIT.get(name)
    if not expected:
        return
    actual = (unit or "").strip()
    if not actual:
        raise ValueError(f"「{name}」单位不能为空（目录单位为「{expected}」）")
    if normalize_unit_key(actual) != normalize_unit_key(expected):
        raise ValueError(
            f"「{name}」单位应为「{expected}」，当前为「{actual}」"
        )
