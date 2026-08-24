"""上传 scope 合法性：删除维度字段解析不全则拒绝导入。"""

from __future__ import annotations

from dataclasses import dataclass

from app.common.vehicle_model import normalize_vehicle_model

_PLACEHOLDER_VEHICLE_MODELS = frozenset({"UNKNOWN", "未知车型"})


@dataclass(frozen=True, slots=True)
class StampingProcessUploadScope:
    location: str
    stamping_supplier: str
    vehicle_model: str
    version: str


@dataclass(frozen=True, slots=True)
class BomMaterialUploadScope:
    location: str
    vehicle_model: str
    bom_version: str


def _missing_label_text(labels: list[str]) -> str:
    return "、".join(labels)


def _require_nonempty_text(
    value: str | None,
    label: str,
    missing: list[str],
) -> str:
    text = (value or "").strip()
    if not text:
        missing.append(label)
        return ""
    return text


def _require_vehicle_model(
    value: str | None,
    label: str,
    missing: list[str],
) -> str:
    normalized = normalize_vehicle_model(value)
    if not normalized or normalized in _PLACEHOLDER_VEHICLE_MODELS:
        missing.append(label)
        return ""
    return normalized


def validate_stamping_process_upload_scope(
    *,
    location: str,
    stamping_supplier: str | None,
    vehicle_model: str | None,
    version: str | None,
) -> StampingProcessUploadScope:
    """
    冲压工艺表导入 scope：基地 + 冲压工厂 + 车型 + 版本（与删除旧数据维度一致）。
    """
    missing: list[str] = []
    loc = _require_nonempty_text(location, "基地", missing)
    supplier = _require_nonempty_text(stamping_supplier, "冲压工厂", missing)
    ver = _require_nonempty_text(version, "版本", missing)
    vehicle = _require_vehicle_model(vehicle_model, "车型", missing)

    if missing:
        raise ValueError(
            f"Excel 头信息不完整，无法导入：缺少{_missing_label_text(missing)}。"
            "请检查表头是否填写冲压承制公司、车型（项目名称）与版本。"
        )

    return StampingProcessUploadScope(
        location=loc,
        stamping_supplier=supplier,
        vehicle_model=vehicle,
        version=ver,
    )


def validate_bom_material_upload_scope(
    *,
    location: str,
    vehicle_model: str | None,
    bom_version: str | None,
) -> BomMaterialUploadScope:
    """
    焊接工程材料清单导入 scope：基地 + 项目代号 + 版本（与快照唯一键一致）。
    """
    missing: list[str] = []
    loc = _require_nonempty_text(location, "基地", missing)
    ver = _require_nonempty_text(bom_version, "版本", missing)
    vehicle = _require_vehicle_model(vehicle_model, "项目", missing)

    if missing:
        raise ValueError(
            f"Excel 头信息不完整，无法导入：缺少{_missing_label_text(missing)}。"
            "请检查表头是否填写项目代号与版本。"
        )

    return BomMaterialUploadScope(
        location=loc,
        vehicle_model=vehicle,
        bom_version=ver,
    )
