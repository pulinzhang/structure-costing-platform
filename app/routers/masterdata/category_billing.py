"""计费管理。按分类查看，一次保存勾选。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.category_billing_dto import (
    AssemblyCategoryBillingQuery,
    CategoryBillingReplace,
)
from app.schemas.vo.category_billing_vo import (
    AssemblyCategoryBillingVO,
    CategoryBillingSelectionVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.category_billing.service import AssemblyCategoryBillingService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/masterdata/category-billings", tags=["计费管理"])

_service = AssemblyCategoryBillingService()


@router.get(
    "",
    response_model=ApiResponse[PageResult[AssemblyCategoryBillingVO]],
    summary="分页查询计费",
)
def list_category_billings(
    query: AssemblyCategoryBillingQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.CATEGORY_BILLING_VIEW)),
) -> ApiResponse[PageResult[AssemblyCategoryBillingVO]]:
    items, total = _service.list_page(db, query)
    return ApiResponse.list_(items=items, total=total, page=query.page, page_size=query.size)


@router.put(
    "/categories/{category_id:int}",
    response_model=ApiResponse[CategoryBillingSelectionVO],
    summary="保存某个分类勾选的费用",
)
def replace_category_billing(
    category_id: int,
    dto: CategoryBillingReplace,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.CATEGORY_BILLING_UPDATE)),
) -> ApiResponse[CategoryBillingSelectionVO]:
    selection = _service.replace_selection(db, category_id, dto, current_user=current_user)
    return ApiResponse.updated(data=selection, message="保存成功")
