"""基地主数据 CRUD。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.dto.location_dto import (
    LocationAliasCreateDTO,
    LocationCreateDTO,
    LocationUpdateDTO,
)
from app.schemas.vo.location_vo import LocationVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.location import LocationService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/masterdata/locations", tags=["基地"])

_service = LocationService()


@router.get("", response_model=ApiResponse[list[LocationVO]])
def list_locations(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LOCATION_VIEW)),
) -> ApiResponse[list[LocationVO]]:
    items = _service.list_all(db)
    return ApiResponse.ok(data=items, message=f"查询到 {len(items)} 条记录")


@router.post(
    "",
    response_model=ApiResponse[LocationVO],
    status_code=status.HTTP_201_CREATED,
)
def create_location(
    dto: LocationCreateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LOCATION_CREATE)),
) -> ApiResponse[LocationVO]:
    record = _service.create(db, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.patch("/{location}", response_model=ApiResponse[LocationVO])
def update_location(
    location: str,
    dto: LocationUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LOCATION_UPDATE)),
) -> ApiResponse[LocationVO]:
    record = _service.update(db, location, dto, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete("/{location}", response_model=ApiResponse[None])
def delete_location(
    location: str,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LOCATION_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, location)
    return ApiResponse.deleted(message="删除成功")


@router.post(
    "/{location}/aliases",
    response_model=ApiResponse[LocationVO],
    status_code=status.HTTP_201_CREATED,
)
def add_location_alias(
    location: str,
    dto: LocationAliasCreateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LOCATION_CREATE)),
) -> ApiResponse[LocationVO]:
    record = _service.add_alias(db, location, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="别名已添加")


@router.delete(
    "/{location}/aliases/{alias}",
    response_model=ApiResponse[LocationVO],
)
def delete_location_alias(
    location: str,
    alias: str,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LOCATION_UPDATE)),
) -> ApiResponse[LocationVO]:
    record = _service.delete_alias(db, location, alias, current_user=current_user)
    return ApiResponse.ok(data=record, message="别名已删除")
