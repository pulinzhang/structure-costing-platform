"""冲压检具费：筛选、模板、同步上传、列表、整包删除。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.exceptions.base import BusinessException
from app.schemas.common.page_result import PageResult
from app.schemas.dto.stamping_gauge_fee_dto import StampingGaugeFeeQuery, StampingGaugeFeeUpdate
from app.schemas.vo.stamping_gauge_fee_vo import (
    StampingGaugeFeeFilterVO,
    StampingGaugeFeeImportResultVO,
    StampingGaugeFeeScopeDeleteResultVO,
    StampingGaugeFeeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.gauge_fee.export.service import StampingGaugeFeeExportService
from app.services.stamping.gauge_fee.service import StampingGaugeFeeService
from app.services.stamping.gauge_fee.upload.upload_service import StampingGaugeFeeUploadService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/stamping/gauge-fees", tags=["冲压检具费"])

_service = StampingGaugeFeeService()
_upload_service = StampingGaugeFeeUploadService()
_export_service = StampingGaugeFeeExportService()


@router.get(
    "/filters",
    response_model=ApiResponse[StampingGaugeFeeFilterVO],
)
def list_gauge_fee_filters(
    location: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(Perm.STAMPING_GAUGE_FEE_UPLOAD_VIEW, Perm.STAMPING_GAUGE_FEE_VIEW)
    ),
) -> ApiResponse[StampingGaugeFeeFilterVO]:
    return ApiResponse.ok(data=_service.list_scope_filters(db, location))


@router.get("/template")
def download_gauge_fee_template(
    location: str = Query(...),
    vehicle_model: str = Query(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_GAUGE_FEE_UPLOAD_VIEW)),
) -> StreamingResponse:
    content, filename = _upload_service.build_template(
        db, location=location, vehicle_model=vehicle_model
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/upload",
    response_model=ApiResponse[StampingGaugeFeeImportResultVO],
)
async def upload_gauge_fees(
    location: str = Form(...),
    vehicle_model: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_GAUGE_FEE_UPLOAD_UPLOAD)),
) -> ApiResponse[StampingGaugeFeeImportResultVO]:
    if not file.filename:
        raise BusinessException("未提供文件名")
    file_content = await file.read()
    result = _upload_service.import_excel(
        db,
        file_content=file_content,
        filename=file.filename,
        location=location,
        vehicle_model=vehicle_model,
        current_user=current_user,
    )
    return ApiResponse.ok(data=result, message=result.message)


@router.get(
    "",
    response_model=ApiResponse[PageResult[StampingGaugeFeeVO]],
)
def list_gauge_fees(
    query: StampingGaugeFeeQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_GAUGE_FEE_VIEW)),
) -> ApiResponse[PageResult[StampingGaugeFeeVO]]:
    items, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
    )


@router.get("/export")
def export_gauge_fees(
    query: StampingGaugeFeeQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_GAUGE_FEE_EXPORT)),
) -> StreamingResponse:
    content, filename = _export_service.export(
        db,
        location=query.location,
        vehicle_model=query.vehicle_model,
        part_number=query.part_number,
        status=query.status,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.delete(
    "/scope",
    response_model=ApiResponse[StampingGaugeFeeScopeDeleteResultVO],
)
def delete_gauge_fee_scope(
    location: str = Query(...),
    vehicle_model: str = Query(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_GAUGE_FEE_DELETE)),
) -> ApiResponse[StampingGaugeFeeScopeDeleteResultVO]:
    result = _service.delete_scope(db, location=location, vehicle_model=vehicle_model)
    return ApiResponse.ok(data=result, message=result.message)


@router.put(
    "/{record_id:int}",
    response_model=ApiResponse[StampingGaugeFeeVO],
)
def update_gauge_fee(
    record_id: int,
    dto: StampingGaugeFeeUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_GAUGE_FEE_UPDATE)),
) -> ApiResponse[StampingGaugeFeeVO]:
    record = _service.update(db, record_id, dto, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete(
    "/{record_id:int}",
    response_model=ApiResponse[None],
)
def delete_gauge_fee(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_GAUGE_FEE_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, record_id)
    return ApiResponse.deleted(message="删除成功")
