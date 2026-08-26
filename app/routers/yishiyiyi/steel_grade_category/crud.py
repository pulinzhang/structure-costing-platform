"""牌号分类档案路由。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common import PageResult
from app.schemas.dto.steel_grade_category_dto import (
    SteelGradeCategoryCreate,
    SteelGradeCategoryExportQuery,
    SteelGradeCategoryQuery,
    SteelGradeCategoryUpdate,
)
from app.schemas.vo.steel_grade_category_vo import (
    SteelGradeCategoryOptionVO,
    SteelGradeCategoryVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.yishiyiyi.steel_grade_category import SteelGradeCategoryService
from app.services.yishiyiyi.steel_grade_category.export_service import (
    SteelGradeCategoryExportService,
)
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/yishiyiyi/steel-grade-category", tags=["牌号分类"])

_service = SteelGradeCategoryService()
_export_service = SteelGradeCategoryExportService()


@router.get(
    "/categories",
    response_model=ApiResponse[list[SteelGradeCategoryOptionVO]],
)
def list_canonical_categories(
    current_user: UserVO = Depends(require_perm(Perm.STEEL_GRADE_CATEGORY_VIEW)),
) -> ApiResponse[list[SteelGradeCategoryOptionVO]]:
    return ApiResponse.ok(data=_service.list_canonical_categories())


@router.get(
    "",
    response_model=ApiResponse[PageResult[SteelGradeCategoryVO]],
)
def list_steel_grade_categories(
    query: SteelGradeCategoryQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_GRADE_CATEGORY_VIEW)),
) -> ApiResponse[PageResult[SteelGradeCategoryVO]]:
    items, total = _service.paginate(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
    )


@router.get(
    "/export",
    response_model=None,
)
def export_steel_grade_categories(
    query: SteelGradeCategoryExportQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_GRADE_CATEGORY_EXPORT)),
) -> StreamingResponse:
    content, filename = _export_service.export(db, query)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "/{record_id}",
    response_model=ApiResponse[SteelGradeCategoryVO],
)
def get_steel_grade_category(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_GRADE_CATEGORY_VIEW)),
) -> ApiResponse[SteelGradeCategoryVO]:
    return ApiResponse.ok(data=_service.get_by_id(db, record_id))


@router.post(
    "",
    response_model=ApiResponse[SteelGradeCategoryVO],
    status_code=status.HTTP_201_CREATED,
)
def create_steel_grade_category(
    dto: SteelGradeCategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_GRADE_CATEGORY_CREATE)),
) -> ApiResponse[SteelGradeCategoryVO]:
    record = _service.create(db, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.put(
    "/{record_id}",
    response_model=ApiResponse[SteelGradeCategoryVO],
)
def update_steel_grade_category(
    record_id: int,
    dto: SteelGradeCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_GRADE_CATEGORY_UPDATE)),
) -> ApiResponse[SteelGradeCategoryVO]:
    record = _service.update(db, record_id, dto, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete(
    "/{record_id}",
    response_model=ApiResponse[None],
)
def delete_steel_grade_category(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_GRADE_CATEGORY_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, record_id)
    return ApiResponse.deleted(message="删除成功")
