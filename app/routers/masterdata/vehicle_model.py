"""项目主数据：列表 / 手工创建 / 改期与供货台数 / 删除 / 模板 / 上传 / 导出。

路径（零例外）：复合字符串键 /{location}/{vehicle_model}，禁止 :int；
/template、/export、/upload 必须全部写在该参数路径之前（api-type-safety.mdc §6）。
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.dto.vehicle_model_dto import VehicleModelCreateDTO, VehicleModelUpdateDTO
from app.schemas.vo.user_vo import UserVO
from app.schemas.vo.vehicle_model_vo import (
    VehicleModelListVO,
    VehicleModelUploadResultVO,
    VehicleModelVO,
)
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/masterdata/vehicle-models", tags=["项目"])

_service = VehicleModelService()


@router.get("", response_model=ApiResponse[VehicleModelListVO], summary="查询项目列表")
def list_vehicle_models(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.VEHICLE_MODEL_LIST_VIEW)),
) -> ApiResponse[VehicleModelListVO]:
    data = _service.list_page(db)
    return ApiResponse.ok(data=data, message=f"查询到 {len(data.items)} 条记录")


@router.post(
    "",
    response_model=ApiResponse[VehicleModelVO],
    status_code=status.HTTP_201_CREATED,
    summary="新建项目",
)
def create_vehicle_model(
    dto: VehicleModelCreateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.VEHICLE_MODEL_LIST_CREATE)),
) -> ApiResponse[VehicleModelVO]:
    record = _service.create(db, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.get("/template", summary="下载项目导入模板")
def download_import_template(
    current_user: UserVO = Depends(require_perm(Perm.VEHICLE_MODEL_UPLOAD_VIEW)),
) -> StreamingResponse:
    content, filename = _service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/export", summary="导出项目")
def export_vehicle_models(
    location: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.VEHICLE_MODEL_LIST_EXPORT)),
) -> StreamingResponse:
    content, filename = _service.export_excel(
        db,
        current_user=current_user,
        location=location,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/upload", response_model=ApiResponse[VehicleModelUploadResultVO], summary="同步导入项目"
)
async def upload_vehicle_models(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.VEHICLE_MODEL_UPLOAD_UPLOAD)),
) -> ApiResponse[VehicleModelUploadResultVO]:
    content = await file.read()
    result = _service.process_upload(db, file_content=content, current_user=current_user)
    message = f"导入成功：新增 {result.created_count}，跳过 {result.skipped_count}"
    return ApiResponse.ok(data=result, message=message)


@router.patch(
    "/{location}/{vehicle_model}", response_model=ApiResponse[VehicleModelVO], summary="更新项目"
)
def update_vehicle_model(
    location: str,
    vehicle_model: str,
    dto: VehicleModelUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.VEHICLE_MODEL_LIST_UPDATE)),
) -> ApiResponse[VehicleModelVO]:
    record = _service.update(
        db,
        location,
        vehicle_model,
        dto,
        current_user=current_user,
    )
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete("/{location}/{vehicle_model}", response_model=ApiResponse[None], summary="删除项目")
def delete_vehicle_model(
    location: str,
    vehicle_model: str,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.VEHICLE_MODEL_LIST_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, location, vehicle_model)
    return ApiResponse.deleted(message="删除成功")
