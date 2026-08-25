"""月度核价核对合册 — 导出 API。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.vo.user_vo import UserVO
from app.services.costing.monthly_bundle_export import MonthlyBundleExportService

router = APIRouter(
    prefix="/api/costing/monthly-bundle",
    tags=["月度核价核对合册"],
)

_export_service = MonthlyBundleExportService()


@router.get("/export-download")
def export_download(
    year: int = Query(..., ge=2000, le=2100, description="年度"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    location: str = Query(..., min_length=1, description="基地"),
    vehicle_model: str = Query(..., min_length=1, description="项目"),
    bom_version: str = Query(..., min_length=1, description="BOM 版本"),
    stamping_supplier: str | None = Query(None, description="冲压工厂（可选）"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_EXPORT)),
) -> StreamingResponse:
    """
    导出月度核对合册：成品核价 + 冲压零件核价 + 焊接费 + 加工费 + 钢材联动等。

    须选定年/月/基地/项目/BOM 版本；冲压侧不按 BOM 版本过滤。
    """
    content, filename = _export_service.export(
        db,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        stamping_supplier=stamping_supplier,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )
