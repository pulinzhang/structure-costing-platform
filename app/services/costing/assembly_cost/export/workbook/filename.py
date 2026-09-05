"""导出文件名。"""

from app.common.timezone import now
from app.services.costing.assembly_cost.export.workbook.columns import PROCUREMENT_FILE_PREFIX


def safe_filename_part(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for char in '\\/:*?"<>|':
        text = text.replace(char, "-")
    return text or None


def build_export_filename(
    *,
    view: str,
    year: int | None,
    month: int | None,
    location: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
) -> str:
    if view == "procurement":
        prefix = PROCUREMENT_FILE_PREFIX
        period = f"{year}年{month:02d}月" if year and month else (f"{year}年" if year else None)
        scope_parts = [period, location, vehicle_model, bom_version]
    else:
        prefix = "成品核价"
        scope_parts = [
            f"{year}年" if year else None,
            f"{month}月" if month else None,
            location,
            vehicle_model,
            bom_version,
        ]
    scope = (
        "_".join(part for part in (safe_filename_part(item) for item in scope_parts) if part)
        or "筛选"
    )
    stamp = now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{scope}_{stamp}.xlsx"
