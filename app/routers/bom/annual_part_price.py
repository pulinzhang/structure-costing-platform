"""
BOM 年度零件价路由
API 接口定义（外购 + L1 一口价合并单表）
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.bom_annual_part_price_dto import (
    BomAnnualPartPriceBatchApproveDTO,
    BomAnnualPartPriceBatchDeleteDTO,
    BomAnnualPartPriceBatchReverseAuditDTO,
    BomAnnualPartPriceCreate,
    BomAnnualPartPriceQuery,
    BomAnnualPartPriceUpdate,
)
from app.schemas.vo.bom_annual_part_price_vo import (
    BomAnnualPartPriceBatchAuditResultVO,
    BomAnnualPartPriceBatchDeleteResultVO,
    BomAnnualPartPriceImportResultVO,
    BomAnnualPartPriceResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.annual_part_price.export.service import (
    BomAnnualPartPriceExportService,
)
from app.services.bom.annual_part_price.importing.service import (
    BomAnnualPartPriceImportService,
)
from app.services.bom.annual_part_price.service import BomAnnualPartPriceService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/bom/annual-part-price", tags=["BOM 年度零件价 API"])

_service = BomAnnualPartPriceService()
_export_service = BomAnnualPartPriceExportService()
_import_service = BomAnnualPartPriceImportService()


@router.get(
    "/paginate",
    response_model=ApiResponse[PageResult[BomAnnualPartPriceResponse]],
)
def paginate(
    query: BomAnnualPartPriceQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_VIEW)),
) -> ApiResponse[PageResult[BomAnnualPartPriceResponse]]:
    """分页查询年度零件价"""
    rows, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get("/filters/locations", response_model=ApiResponse[list[str]])
def get_locations(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_VIEW)),
) -> ApiResponse[list[str]]:
    """获取所有基地列表"""
    data = _service.get_locations(db)
    return ApiResponse.ok(data=data)


@router.get("/filters/years", response_model=ApiResponse[list[int]])
def get_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_VIEW)),
) -> ApiResponse[list[int]]:
    """获取所有年份列表"""
    data = _service.get_years(db)
    return ApiResponse.ok(data=data)


@router.get("/export")
def export_excel(
    location: str | None = Query(None, description="采购基地"),
    year: int | None = Query(None, ge=2000, le=2100, description="年份"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_EXPORT)),
) -> StreamingResponse:
    """按当前筛选条件导出年度零件价 Excel（含基地/年份/审核列；导入列可再导入）。"""
    content, filename = _export_service.export(
        db,
        location=location.strip() if location else None,
        year=year,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/template")
def download_import_template(
    location: str = Query(..., description="采购基地"),
    vehicle_model: str = Query(..., description="项目"),
    year: int = Query(..., ge=2000, le=2100, description="年度"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_UPLOAD_VIEW)),
) -> StreamingResponse:
    """下载年度零件价导入模板（该基地该项目 BOM 外购叶子）。"""
    content, filename = _import_service.build_template(
        db, location=location, vehicle_model=vehicle_model, year=year
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/upload",
    response_model=ApiResponse[BomAnnualPartPriceImportResultVO],
)
async def upload_excel(
    location: str = Form(..., description="采购基地（必填）"),
    year: int = Form(..., description="年度（必填）"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_UPLOAD_UPLOAD)),
) -> ApiResponse[BomAnnualPartPriceImportResultVO]:
    """同步导入年度零件价 Excel；基地与年度必选；仅支持 .xlsx。"""
    content = await file.read()
    result = _import_service.import_excel(
        db,
        file_content=content,
        filename=file.filename or "",
        location=location.strip(),
        year=year,
        current_user=current_user,
    )
    return ApiResponse.ok(data=result, message=result.message)


@router.post(
    "/batch-delete",
    response_model=ApiResponse[BomAnnualPartPriceBatchDeleteResultVO],
)
def batch_delete(
    body: BomAnnualPartPriceBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_DELETE)),
) -> ApiResponse[BomAnnualPartPriceBatchDeleteResultVO]:
    """按基地 + 年度批量删除（仅删未审核；已通过跳过）。"""
    result = _service.batch_delete_by_location_year(
        db,
        location=body.location,
        year=body.year,
    )
    return ApiResponse.ok(data=result, message=result.message)


@router.post(
    "/batch-approve",
    response_model=ApiResponse[BomAnnualPartPriceBatchAuditResultVO],
)
def batch_approve(
    body: BomAnnualPartPriceBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_APPROVE)),
) -> ApiResponse[BomAnnualPartPriceBatchAuditResultVO]:
    """按基地 + 年度批量审核通过。"""
    result = _service.batch_approve(db, body, current_user=current_user)
    return ApiResponse.ok(data=result, message=result.message)


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[BomAnnualPartPriceBatchAuditResultVO],
)
def batch_reverse_audit(
    body: BomAnnualPartPriceBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_REVERSE)),
) -> ApiResponse[BomAnnualPartPriceBatchAuditResultVO]:
    """按基地 + 年度批量反审核。"""
    result = _service.batch_reverse_audit(db, body, current_user=current_user)
    return ApiResponse.ok(data=result, message=result.message)


@router.post(
    "",
    response_model=ApiResponse[BomAnnualPartPriceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: BomAnnualPartPriceCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_CREATE)),
) -> ApiResponse[BomAnnualPartPriceResponse]:
    """创建年度零件价记录"""
    record = _service.create(db, body, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.get("/{id:int}", response_model=ApiResponse[BomAnnualPartPriceResponse])
def get_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_VIEW)),
) -> ApiResponse[BomAnnualPartPriceResponse]:
    """获取单个年度零件价记录"""
    record = _service.get_by_id(db, id)
    return ApiResponse.ok(data=record, message="获取成功")


@router.put("/{id:int}", response_model=ApiResponse[BomAnnualPartPriceResponse])
def update(
    id: int,
    body: BomAnnualPartPriceUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_UPDATE)),
) -> ApiResponse[BomAnnualPartPriceResponse]:
    """更新年度零件价记录"""
    record = _service.update(db, id, body, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete("/{id:int}", response_model=ApiResponse[None])
def delete(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_ANNUAL_PART_PRICE_DELETE)),
) -> ApiResponse[None]:
    """删除年度零件价记录"""
    _service.delete(db, id)
    return ApiResponse.deleted(message="删除成功")
