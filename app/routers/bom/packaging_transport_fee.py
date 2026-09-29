"""
BOM 包装运输费路由
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
)
from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.bom_packaging_transport_fee_dto import (
    BomPackagingTransportFeeBatchApproveDTO,
    BomPackagingTransportFeeBatchDeleteDTO,
    BomPackagingTransportFeeBatchReverseAuditDTO,
    BomPackagingTransportFeeCreate,
    BomPackagingTransportFeeQuery,
    BomPackagingTransportFeeUpdate,
)
from app.schemas.vo.bom_packaging_transport_fee_vo import (
    BomPackagingTransportFeeBatchAuditResultVO,
    BomPackagingTransportFeeBatchDeleteResultVO,
    BomPackagingTransportFeeImportResultVO,
    BomPackagingTransportFeeResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.packaging_transport_fee.export.service import (
    BomPackagingTransportFeeExportService,
)
from app.services.bom.packaging_transport_fee.importing.service import (
    BomPackagingTransportFeeImportService,
)
from app.services.bom.packaging_transport_fee.service import BomPackagingTransportFeeService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/bom/packaging-transport-fee", tags=["BOM 包装运输费 API"])

_service = BomPackagingTransportFeeService()
_export_service = BomPackagingTransportFeeExportService()
_import_service = BomPackagingTransportFeeImportService()


@router.get(
    "/paginate",
    response_model=ApiResponse[PageResult[BomPackagingTransportFeeResponse]],
    summary="分页查询包装运输费",
)
def paginate(
    query: BomPackagingTransportFeeQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_VIEW)),
) -> ApiResponse[PageResult[BomPackagingTransportFeeResponse]]:
    rows, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get(
    "/filters/locations", response_model=ApiResponse[list[str]], summary="获取包装运输费基地列表"
)
def get_locations(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_VIEW)),
) -> ApiResponse[list[str]]:
    return ApiResponse.ok(data=_service.get_locations(db))


@router.get(
    "/filters/years", response_model=ApiResponse[list[int]], summary="获取包装运输费年份列表"
)
def get_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_VIEW)),
) -> ApiResponse[list[int]]:
    return ApiResponse.ok(data=_service.get_years(db))


@router.get(
    "/filters/vehicle-models",
    response_model=ApiResponse[list[str]],
    summary="获取包装运输费项目列表",
)
def get_vehicle_models(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_VIEW)),
) -> ApiResponse[list[str]]:
    return ApiResponse.ok(data=_service.get_vehicle_models(db))


@router.get("/export", summary="按筛选导出包装运输费")
def export_excel(
    location: str | None = Query(None, description="采购基地"),
    year: int | None = Query(None, ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="年份"),
    vehicle_model: str | None = Query(None, description="项目"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_EXPORT)),
) -> StreamingResponse:
    content, filename = _export_service.export(
        db,
        location=location.strip() if location else None,
        year=year,
        vehicle_model=vehicle_model.strip() if vehicle_model else None,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/template", summary="下载包装运输费导入模板")
def download_import_template(
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_UPLOAD_VIEW)),
) -> StreamingResponse:
    content, filename = _import_service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/upload",
    response_model=ApiResponse[BomPackagingTransportFeeImportResultVO],
    summary="同步导入包装运输费",
)
async def upload_excel(
    location: str = Form(..., description="采购基地（必填）"),
    year: int = Form(..., description="年度（必填）"),
    vehicle_model: str = Form(..., description="项目（必填）"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_UPLOAD_UPLOAD)),
) -> ApiResponse[BomPackagingTransportFeeImportResultVO]:
    content = await file.read()
    result = _import_service.import_excel(
        db,
        file_content=content,
        filename=file.filename or "",
        location=location.strip(),
        year=year,
        vehicle_model=vehicle_model.strip(),
        current_user=current_user,
    )
    return ApiResponse.ok(data=result, message=result.message)


@router.post(
    "/batch-delete",
    response_model=ApiResponse[BomPackagingTransportFeeBatchDeleteResultVO],
    summary="按范围批量删除包装运输费",
)
def batch_delete(
    body: BomPackagingTransportFeeBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_DELETE)),
) -> ApiResponse[BomPackagingTransportFeeBatchDeleteResultVO]:
    result = _service.batch_delete_by_scope(
        db,
        location=body.location,
        year=body.year,
        vehicle_model=body.vehicle_model,
    )
    return ApiResponse.ok(data=result, message=result.message)


@router.post(
    "/batch-approve",
    response_model=ApiResponse[BomPackagingTransportFeeBatchAuditResultVO],
    summary="按范围批量审核通过包装运输费",
)
def batch_approve(
    body: BomPackagingTransportFeeBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_APPROVE)),
) -> ApiResponse[BomPackagingTransportFeeBatchAuditResultVO]:
    result = _service.batch_approve(db, body, current_user=current_user)
    return ApiResponse.ok(data=result, message=result.message)


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[BomPackagingTransportFeeBatchAuditResultVO],
    summary="按范围批量反审核包装运输费",
)
def batch_reverse_audit(
    body: BomPackagingTransportFeeBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_REVERSE)),
) -> ApiResponse[BomPackagingTransportFeeBatchAuditResultVO]:
    result = _service.batch_reverse_audit(db, body, current_user=current_user)
    return ApiResponse.ok(data=result, message=result.message)


@router.post(
    "",
    response_model=ApiResponse[BomPackagingTransportFeeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="创建包装运输费",
)
def create(
    body: BomPackagingTransportFeeCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_CREATE)),
) -> ApiResponse[BomPackagingTransportFeeResponse]:
    record = _service.create(db, body, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.get(
    "/{id:int}",
    response_model=ApiResponse[BomPackagingTransportFeeResponse],
    summary="查看包装运输费",
)
def get_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_VIEW)),
) -> ApiResponse[BomPackagingTransportFeeResponse]:
    record = _service.get_by_id(db, id)
    return ApiResponse.ok(data=record, message="获取成功")


@router.put(
    "/{id:int}",
    response_model=ApiResponse[BomPackagingTransportFeeResponse],
    summary="更新包装运输费",
)
def update(
    id: int,
    body: BomPackagingTransportFeeUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_UPDATE)),
) -> ApiResponse[BomPackagingTransportFeeResponse]:
    record = _service.update(db, id, body, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete("/{id:int}", response_model=ApiResponse[None], summary="删除包装运输费")
def delete(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PACKAGING_TRANSPORT_FEE_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, id)
    return ApiResponse.deleted(message="删除成功")
