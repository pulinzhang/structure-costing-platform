"""工程变更单列表 / 详情 / 回滚 API。原件下载走文件溯源。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.engineering_change_dto import EngineeringChangeOrderQueryDTO
from app.schemas.vo.engineering_change_vo import (
    EngineeringChangeDetailVO,
    EngineeringChangeListRowVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.list.query_service import EngineeringChangeQueryService
from app.services.engineering_change.list.rollback_service import EngineeringChangeRollbackService
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


@router.get(
    "/change-orders/{upload_log_id}",
    response_model=ApiResponse[EngineeringChangeDetailVO],
)
def get_change_order_upload(
    upload_log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_ORDER_LIST_VIEW)),
) -> ApiResponse[EngineeringChangeDetailVO]:
    _ = current_user
    return ApiResponse.ok(data=_query_service.get_detail(db, upload_log_id))


@router.delete(
    "/change-orders/{upload_log_id}",
    response_model=ApiResponse[None],
)
def delete_change_order_upload(
    upload_log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_ORDER_LIST_DELETE)),
) -> ApiResponse[None]:
    _rollback_service.rollback(db, upload_log_id, current_user)
    return ApiResponse.deleted(message="已删除并回滚本次工程变更")
