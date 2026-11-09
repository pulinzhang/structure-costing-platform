"""总成分类。静态路径写在 /{record_id:int} 之前。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.assembly_category_dto import (
    AssemblyCategoryCreate,
    AssemblyCategoryQuery,
    AssemblyCategoryUpdate,
)
from app.schemas.vo.assembly_category_vo import AssemblyCategoryVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.assembly_category.service import AssemblyCategoryService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/masterdata/assembly-categories", tags=["总成分类"])

_service = AssemblyCategoryService()


@router.get(
    "", response_model=ApiResponse[PageResult[AssemblyCategoryVO]], summary="分页查询总成分类"
)
def list_assembly_categories(
    query: AssemblyCategoryQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_CATEGORY_VIEW)),
) -> ApiResponse[PageResult[AssemblyCategoryVO]]:
    items, total = _service.list_page(db, query)
    return ApiResponse.list_(items=items, total=total, page=query.page, page_size=query.size)


@router.post(
    "",
    response_model=ApiResponse[AssemblyCategoryVO],
    status_code=status.HTTP_201_CREATED,
    summary="新建总成分类",
)
def create_assembly_category(
    dto: AssemblyCategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_CATEGORY_CREATE)),
) -> ApiResponse[AssemblyCategoryVO]:
    record = _service.create(db, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.put(
    "/{record_id:int}",
    response_model=ApiResponse[AssemblyCategoryVO],
    summary="编辑总成分类",
)
def update_assembly_category(
    record_id: int,
    dto: AssemblyCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_CATEGORY_UPDATE)),
) -> ApiResponse[AssemblyCategoryVO]:
    record = _service.update(db, record_id, dto, current_user=current_user)
    return ApiResponse.updated(data=record)


@router.delete(
    "/{record_id:int}",
    response_model=ApiResponse[None],
    summary="删除总成分类",
)
def delete_assembly_category(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_CATEGORY_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, record_id)
    return ApiResponse.deleted()
