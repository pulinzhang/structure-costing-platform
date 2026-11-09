"""费用档案。静态路径写在 /{record_id:int} 之前。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.fee_archive_dto import FeeArchiveCreate, FeeArchiveQuery, FeeArchiveUpdate
from app.schemas.vo.fee_archive_vo import FeeArchiveVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.fee_archive.service import FeeArchiveService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/masterdata/fee-archives", tags=["费用档案"])

_service = FeeArchiveService()


@router.get("", response_model=ApiResponse[PageResult[FeeArchiveVO]], summary="分页查询费用档案")
def list_fee_archives(
    query: FeeArchiveQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.FEE_ARCHIVE_VIEW)),
) -> ApiResponse[PageResult[FeeArchiveVO]]:
    items, total = _service.list_page(db, query)
    return ApiResponse.list_(items=items, total=total, page=query.page, page_size=query.size)


@router.post(
    "",
    response_model=ApiResponse[FeeArchiveVO],
    status_code=status.HTTP_201_CREATED,
    summary="新建费用档案",
)
def create_fee_archive(
    dto: FeeArchiveCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.FEE_ARCHIVE_CREATE)),
) -> ApiResponse[FeeArchiveVO]:
    record = _service.create(db, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.put(
    "/{record_id:int}",
    response_model=ApiResponse[FeeArchiveVO],
    summary="编辑费用档案",
)
def update_fee_archive(
    record_id: int,
    dto: FeeArchiveUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.FEE_ARCHIVE_UPDATE)),
) -> ApiResponse[FeeArchiveVO]:
    record = _service.update(db, record_id, dto, current_user=current_user)
    return ApiResponse.updated(data=record)


@router.delete(
    "/{record_id:int}",
    response_model=ApiResponse[None],
    summary="删除费用档案",
)
def delete_fee_archive(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.FEE_ARCHIVE_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, record_id)
    return ApiResponse.deleted()
