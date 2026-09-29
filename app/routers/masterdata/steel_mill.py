"""钢厂档案。静态路径写在 /{record_id:int} 之前。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_mill_dto import SteelMillCreate, SteelMillQuery, SteelMillUpdate
from app.schemas.vo.steel_mill_vo import SteelMillVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.steel_mill.service import SteelMillService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/masterdata/steel-mills", tags=["钢厂"])

_service = SteelMillService()


@router.get("", response_model=ApiResponse[PageResult[SteelMillVO]], summary="分页查询钢厂")
def list_steel_mills(
    query: SteelMillQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_MILL_VIEW)),
) -> ApiResponse[PageResult[SteelMillVO]]:
    items, total = _service.list_page(db, query)
    return ApiResponse.list_(items=items, total=total, page=query.page, page_size=query.size)


@router.post(
    "",
    response_model=ApiResponse[SteelMillVO],
    status_code=status.HTTP_201_CREATED,
    summary="新建钢厂",
)
def create_steel_mill(
    dto: SteelMillCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_MILL_CREATE)),
) -> ApiResponse[SteelMillVO]:
    record = _service.create(db, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.put(
    "/{record_id:int}",
    response_model=ApiResponse[SteelMillVO],
    summary="编辑钢厂",
)
def update_steel_mill(
    record_id: int,
    dto: SteelMillUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_MILL_UPDATE)),
) -> ApiResponse[SteelMillVO]:
    record = _service.update(db, record_id, dto, current_user=current_user)
    return ApiResponse.updated(data=record)


@router.delete(
    "/{record_id:int}",
    response_model=ApiResponse[None],
    summary="删除钢厂",
)
def delete_steel_mill(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_MILL_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, record_id)
    return ApiResponse.deleted()
