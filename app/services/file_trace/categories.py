"""文件溯源分类与业务权限交集。"""

from __future__ import annotations

from app.common.permissions.checks import has_permission
from app.common.permissions.codes import Perm
from app.schemas.vo.user_vo import UserVO

FILE_CATEGORY_LABELS: dict[str, str] = {
    "bom_material": "BOM 材料清单",
    "stamping_process": "冲压工艺",
    "stamping_die": "冲压模具布点",
    "stamping_gauge_fee": "冲压检具费",
    "stamping_tonnage_price": "冲次单价",
    "steel_base_price": "钢价基准价",
    "steel_price_policy": "加减价政策",
    "bom_packaging_transport_fee": "包装运输费",
    "bom_welding_unit_price": "焊接单价",
    "bom_annual_part_price": "年度零件价",
    "bom_procurement_object_supplier": "采购对象供应商",
}

VALID_FILE_CATEGORIES = frozenset(FILE_CATEGORY_LABELS.keys())

CATEGORY_VIEW_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "stamping_process": (
        Perm.STAMPING_UPLOAD_VIEW,
        Perm.STAMPING_PARTS_VIEW,
    ),
    "stamping_die": (
        Perm.STAMPING_DIE_UPLOAD_VIEW,
        Perm.STAMPING_DIE_LIST_VIEW,
    ),
    "stamping_gauge_fee": (
        Perm.STAMPING_GAUGE_FEE_UPLOAD_VIEW,
        Perm.STAMPING_GAUGE_FEE_VIEW,
    ),
    "stamping_tonnage_price": (
        Perm.STAMPING_TONNAGE_UPLOAD_VIEW,
        Perm.STAMPING_TONNAGE_VIEW,
    ),
    "steel_base_price": (
        Perm.BASE_PRICE_UPLOAD_VIEW,
        Perm.BASE_PRICE_DOWNLOAD_VIEW,
    ),
    "steel_price_policy": (
        Perm.STEEL_PRICE_POLICY_UPLOAD_VIEW,
        Perm.STEEL_PRICE_POLICY_DOWNLOAD_VIEW,
    ),
    "bom_material": (
        Perm.BOM_UPLOAD_VIEW,
        Perm.BOM_MATERIAL_VIEW,
    ),
    "bom_packaging_transport_fee": (
        Perm.BOM_PACKAGING_TRANSPORT_FEE_UPLOAD_VIEW,
        Perm.BOM_PACKAGING_TRANSPORT_FEE_VIEW,
    ),
    "bom_welding_unit_price": (
        Perm.BOM_WELDING_UNIT_PRICE_UPLOAD_VIEW,
        Perm.BOM_WELDING_UNIT_PRICE_VIEW,
    ),
    "bom_annual_part_price": (
        Perm.BOM_ANNUAL_PART_PRICE_UPLOAD_VIEW,
        Perm.BOM_ANNUAL_PART_PRICE_VIEW,
    ),
    "bom_procurement_object_supplier": (
        Perm.BOM_PROCUREMENT_OBJECT_SUPPLIER_UPLOAD_VIEW,
        Perm.BOM_PROCUREMENT_OBJECT_LIST_VIEW,
    ),
}


def resolve_allowed_categories(user: UserVO) -> list[str]:
    """由业务 view 权限推导可见分类；admin 全开。"""
    if getattr(user, "is_admin", False):
        return sorted(FILE_CATEGORY_LABELS.keys())
    permissions = getattr(user, "permissions", None) or []
    if "*" in permissions:
        return sorted(FILE_CATEGORY_LABELS.keys())

    allowed: list[str] = []
    for category, perm_codes in CATEGORY_VIEW_PERMISSIONS.items():
        if any(has_permission(user, code) for code in perm_codes):
            allowed.append(category)
    return sorted(allowed)


def category_label(category: str) -> str:
    return FILE_CATEGORY_LABELS.get(category, category)
