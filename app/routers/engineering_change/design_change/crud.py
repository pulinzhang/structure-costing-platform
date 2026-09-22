"""工程变更单列表 / 回滚 API。当时 Excel 从查看抽屉下载。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.engineering_change.design_change import EngineeringChangeOrderQueryDTO
from app.schemas.vo.engineering_change.design_change import EngineeringChangeListRowVO
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.design_change.list.query import EngineeringChangeQueryService
from app.services.engineering_change.design_change.list.rollback import (
    EngineeringChangeRollbackService,
)
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/engineering-change", tags=["工程变更"])

_query_service = EngineeringChangeQueryService()
_rollback_service = EngineeringChangeRollbackService()


@router.get(
    "/change-orders",
    response_model=ApiResponse[PageResult[EngineeringChangeListRowVO]],
)
def list_change_orders(
    query: EngineeringChangeOrderQueryDTO = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_ORDER_LIST_VIEW)),
) -> ApiResponse[PageResult[EngineeringChangeListRowVO]]:
    _ = current_user
    items, total = _query_service.paginate(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条记录",
    )


@router.get("/change-orders/{upload_log_id:int}/original-file")
def download_change_order_original(
    upload_log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_ORDER_LIST_VIEW)),
) -> FileResponse:
    absolute_path, original_filename, media_type = _query_service.resolve_original_file(
        db, upload_log_id, current_user
    )
    encoded_name = quote(original_filename)
    return FileResponse(
        path=str(absolute_path),
        media_type=media_type,
        filename=original_filename,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


@router.delete(
    "/change-orders/{upload_log_id:int}",
    response_model=ApiResponse[None],
)
def delete_change_order_upload(
    upload_log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_ORDER_LIST_DELETE)),
) -> ApiResponse[None]:
    _rollback_service.rollback(db, upload_log_id, current_user)
    return ApiResponse.deleted(message="已删除并回滚本次工程变更")
