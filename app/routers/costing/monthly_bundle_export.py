"""月度核对导出 — 导出 API。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
    MONTH_MAX,
    MONTH_MIN,
)
from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.vo.user_vo import UserVO
from app.services.costing.monthly_bundle_export.export.service import (
    MonthlyBundleExportService,
)

router = APIRouter(
    prefix="/api/costing/monthly-bundle",
    tags=["月度核对导出"],
)

_export_service = MonthlyBundleExportService()


@router.get(
    "/export-download",
    summary="导出月度核对",
)
def export_download(
    year: int = Query(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="年度"),
    month: int = Query(..., ge=MONTH_MIN, le=MONTH_MAX, description="月份"),
    location: str = Query(..., min_length=1, description="基地"),
    vehicle_model: str = Query(..., min_length=1, description="项目"),
    bom_version: str | None = Query(None, description="BOM 版本（可选；空=该月全部）"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_EXPORT)),
) -> StreamingResponse:
    """
    导出月度核对：成品核价 + 冲压零件核价 + 焊接费 + 加工费 + 钢材联动等。

    须选定年/月/基地/项目；版本可选（工程变更后同月可多版本）。
    """
    content, filename = _export_service.export(
        db,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
