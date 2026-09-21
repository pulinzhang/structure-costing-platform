"""冲压模具单价档案：筛选、列表、增删改。"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.stamping_die_unit_price_dto import (
    StampingDieUnitPriceCreate,
    StampingDieUnitPriceQuery,
    StampingDieUnitPriceUpdate,
)
from app.schemas.vo.stamping_die_unit_price_vo import (
    StampingDieUnitPriceFilterVO,
    StampingDieUnitPriceVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.die.unit_price.service import StampingDieUnitPriceService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/stamping/die-unit-prices", tags=["冲压模具单价"])

_service = StampingDieUnitPriceService()


@router.get(
    "/filters",
    response_model=ApiResponse[StampingDieUnitPriceFilterVO],
)
def list_die_unit_price_filters(
    location: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_UNIT_PRICE_VIEW)),
) -> ApiResponse[StampingDieUnitPriceFilterVO]:
    return ApiResponse.ok(data=_service.list_scope_filters(db, location))


@router.get(
    "",
    response_model=ApiResponse[PageResult[StampingDieUnitPriceVO]],
)
def list_die_unit_prices(
    query: StampingDieUnitPriceQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_UNIT_PRICE_VIEW)),
) -> ApiResponse[PageResult[StampingDieUnitPriceVO]]:
    items, total = _service.paginate(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
    )


@router.post(
    "",
    response_model=ApiResponse[StampingDieUnitPriceVO],
    status_code=status.HTTP_201_CREATED,
)
def create_die_unit_price(
    dto: StampingDieUnitPriceCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_UNIT_PRICE_CREATE)),
) -> ApiResponse[StampingDieUnitPriceVO]:
    record = _service.create(db, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.put(
    "/{record_id:int}",
    response_model=ApiResponse[StampingDieUnitPriceVO],
)
def update_die_unit_price(
    record_id: int,
    dto: StampingDieUnitPriceUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_UNIT_PRICE_UPDATE)),
) -> ApiResponse[StampingDieUnitPriceVO]:
    record = _service.update(db, record_id, dto, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete(
    "/{record_id:int}",
    response_model=ApiResponse[None],
)
def delete_die_unit_price(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_UNIT_PRICE_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, record_id)
    return ApiResponse.deleted(message="删除成功")
