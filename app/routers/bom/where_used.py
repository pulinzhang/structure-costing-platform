"""零件用在哪 API。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.dto.bom_where_used_dto import BomWhereUsedQuery
from app.schemas.vo.bom_where_used_vo import BomWhereUsedVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.where_used.export import BomWhereUsedExportService
from app.services.bom.where_used.service import BomWhereUsedService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/bom", tags=["BOM 零件用在哪"])

_service = BomWhereUsedService()
_export_service = BomWhereUsedExportService()


@router.get(
    "/where-used",
    response_model=ApiResponse[BomWhereUsedVO],
)
def search_where_used(
    query: BomWhereUsedQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WHERE_USED_VIEW)),
) -> ApiResponse[BomWhereUsedVO]:
    result = _service.search(db, query)
    return ApiResponse.ok(data=result, message="查询成功")


@router.get("/where-used/export")
def export_where_used(
    query: BomWhereUsedQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WHERE_USED_EXPORT)),
) -> StreamingResponse:
    content, filename = _export_service.export(db, query, current_user)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
