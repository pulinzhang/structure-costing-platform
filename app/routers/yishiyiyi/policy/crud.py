"""
钢价政策管理 API
主表/阶梯明细 CRUD、批量删除、阶梯匹配。
所有尺寸和金额字段全程使用 Decimal/Integer，绝不转为 float。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_price_policy_dto import (
    LadderItemCreate,
    LadderItemUpdate,
    PolicyCreate,
    PolicyMatchRequest,
    PolicyQuery,
    PolicyUpdate,
)
from app.schemas.vo.steel_price_policy_vo import (
    LadderItemResponse,
    PolicyDetailResponse,
    PolicyListResponse,
    PolicyMatchResponse,
    PolicyOptionsResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.yishiyiyi.policy.service import SteelPricePolicyService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/yishiyiyi/policy", tags=["钢价政策管理"])

_policy_service = SteelPricePolicyService()


@router.get(
    "",
    response_model=ApiResponse[PageResult[PolicyListResponse]],
)
def list_policies(
    query: PolicyQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STEEL_PRICE_POLICY_DOWNLOAD_VIEW,
            Perm.STEEL_PRICE_POLICY_UPLOAD_VIEW,
        )
    ),
) -> ApiResponse[PageResult[PolicyListResponse]]:
    """分页筛选政策列表"""
    records, total, options = _policy_service.paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条政策",
        filters=options,
    )


@router.get(
    "/options",
    response_model=ApiResponse[PolicyOptionsResponse],
)
def get_policy_options(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STEEL_PRICE_POLICY_DOWNLOAD_VIEW,
            Perm.STEEL_PRICE_POLICY_UPLOAD_VIEW,
        )
    ),
) -> ApiResponse[PolicyOptionsResponse]:
    """获取政策筛选下拉选项"""
    _, _, options = _policy_service.paginate(db, PolicyQuery(page=1, size=1))
    return ApiResponse.ok(data=options)


@router.delete(
    "/batch",
    response_model=ApiResponse[None],
)
def batch_delete_policies(
    year: int | None = None,
    month: int | None = None,
    steel_mill: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_DOWNLOAD_DELETE)),
) -> ApiResponse[None]:
    """
    根据条件批量删除政策。
    年度、月份必填；钢厂可选（不填则删除该年月下全部钢厂）。
    """
    count = _policy_service.delete_by_conditions(
        db,
        year=year,
        month=month,
        steel_mill=steel_mill,
    )
    return ApiResponse.deleted(message=f"成功删除 {count} 条政策")


@router.post(
    "/match",
    response_model=ApiResponse[PolicyMatchResponse],
)
def match_ladder(
    body: PolicyMatchRequest,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STEEL_PRICE_POLICY_DOWNLOAD_VIEW,
            Perm.STEEL_PRICE_CALC_VIEW,
            Perm.STEEL_PRICE_LIST_VIEW,
        )
    ),
) -> ApiResponse[PolicyMatchResponse]:
    """
    根据政策维度与尺寸值，匹配阶梯明细并返回加减价金额。
    - 命中多条时以 sort_order 升序、id 升序确定优先级
    - price_adjustment 为整数（元/吨）
    """
    result = _policy_service.match(db, body)
    return ApiResponse.ok(data=result)


@router.get(
    "/{policy_id:int}",
    response_model=ApiResponse[PolicyDetailResponse],
)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STEEL_PRICE_POLICY_DOWNLOAD_VIEW,
            Perm.STEEL_PRICE_POLICY_UPLOAD_VIEW,
        )
    ),
) -> ApiResponse[PolicyDetailResponse]:
    """获取政策详情（含完整阶梯明细，按 sort_order + id 排序）"""
    record = _policy_service.get_by_id(db, policy_id)
    return ApiResponse.ok(data=record)


@router.post(
    "",
    response_model=ApiResponse[PolicyDetailResponse],
)
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_UPLOAD_UPLOAD)),
) -> ApiResponse[PolicyDetailResponse]:
    """原子创建政策（含阶梯明细）"""
    record = _policy_service.create(db, body, current_user=current_user)
    return ApiResponse.created(data=record, message="政策创建成功")


@router.put(
    "/{policy_id:int}",
    response_model=ApiResponse[PolicyDetailResponse],
)
def update_policy(
    policy_id: int,
    body: PolicyUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_UPLOAD_UPLOAD)),
) -> ApiResponse[PolicyDetailResponse]:
    """更新政策（支持更新政策头字段和整组替换阶梯明细）"""
    record = _policy_service.update(db, policy_id, body, current_user=current_user)
    return ApiResponse.updated(data=record, message="政策更新成功")


@router.delete(
    "/{policy_id:int}",
    response_model=ApiResponse[None],
)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_DOWNLOAD_DELETE)),
) -> ApiResponse[None]:
    """删除政策（含级联删除全部阶梯明细）"""
    _policy_service.delete(db, policy_id)
    return ApiResponse.deleted(message="政策删除成功")


@router.post(
    "/{policy_id:int}/items",
    response_model=ApiResponse[LadderItemResponse],
)
def add_ladder_item(
    policy_id: int,
    body: LadderItemCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_UPLOAD_UPLOAD)),
) -> ApiResponse[LadderItemResponse]:
    """向指定政策新增一条阶梯明细"""
    record = _policy_service.add_item(db, policy_id, body, current_user=current_user)
    return ApiResponse.created(data=record, message="阶梯明细新增成功")


@router.put(
    "/{policy_id:int}/items/{item_id:int}",
    response_model=ApiResponse[LadderItemResponse],
)
def update_ladder_item(
    policy_id: int,
    item_id: int,
    body: LadderItemUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_UPLOAD_UPLOAD)),
) -> ApiResponse[LadderItemResponse]:
    """更新指定政策下的单条阶梯明细"""
    record = _policy_service.update_item(db, item_id, body, current_user=current_user)
    return ApiResponse.updated(data=record, message="阶梯明细更新成功")


@router.delete(
    "/{policy_id:int}/items/{item_id:int}",
    response_model=ApiResponse[None],
)
def delete_ladder_item(
    policy_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_DOWNLOAD_DELETE)),
) -> ApiResponse[None]:
    """删除指定政策下的单条阶梯明细"""
    _policy_service.delete_item(db, item_id)
    return ApiResponse.deleted(message="阶梯明细删除成功")
