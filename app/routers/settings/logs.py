"""操作日志路由。"""

from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.operation_log_dto import OperationLogQuery
from app.schemas.vo.operation_log_vo import OperationLogVO
from app.schemas.vo.user_vo import UserVO
from app.services.settings.logs.service import OperationLogService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/settings/logs", tags=["操作日志"])
_service = OperationLogService()


@router.get(
    "",
    response_model=ApiResponse[PageResult[OperationLogVO]],
    summary="分页查询操作日志",
)
def list_operation_logs(
    query: OperationLogQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_LOGS_VIEW)),
) -> ApiResponse[PageResult[OperationLogVO]]:
    """分页查询操作日志（列表查询本身不记审计）。"""
    rows, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条日志",
    )


@router.get("/export-download", summary="按筛选条件导出操作日志 Excel")
def export_operation_logs(
    username: str | None = Query(None),
    client_ip: str | None = Query(None),
    menu_code: str | None = Query(None),
    permission_code: str | None = Query(None),
    module: str | None = Query(None),
    action: str | None = Query(None),
    method: str | None = Query(None),
    success: bool | None = Query(None),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_LOGS_EXPORT)),
) -> StreamingResponse:
    """按筛选条件导出操作日志 Excel（记入审计）。"""
    content, filename = _service.export(
        db,
        username=username,
        client_ip=client_ip,
        menu_code=menu_code,
        permission_code=permission_code,
        module=module,
        action=action,
        method=method,
        success=success,
        created_from=created_from,
        created_to=created_to,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
