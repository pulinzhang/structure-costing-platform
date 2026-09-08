"""供应商主数据：列表 / 手工创建 / 改启用 / 别名 / 模板 / 上传 / 导出。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common import PageResult
from app.schemas.dto.supplier_dto import (
    SupplierAliasCreateDTO,
    SupplierCreateDTO,
    SupplierQuery,
    SupplierUpdateDTO,
)
from app.schemas.vo.supplier_vo import SupplierUploadResultVO, SupplierVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.supplier import SupplierService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/masterdata/suppliers", tags=["供应商"])

_service = SupplierService()


@router.get("", response_model=ApiResponse[PageResult[SupplierVO]])
def list_suppliers(
    query: SupplierQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SUPPLIER_LIST_VIEW)),
) -> ApiResponse[PageResult[SupplierVO]]:
    items, total = _service.list_page(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
    )


@router.post(
    "",
    response_model=ApiResponse[SupplierVO],
    status_code=status.HTTP_201_CREATED,
)
def create_supplier(
    dto: SupplierCreateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SUPPLIER_LIST_CREATE)),
) -> ApiResponse[SupplierVO]:
    record = _service.create(db, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.get("/template")
def download_import_template(
    current_user: UserVO = Depends(require_perm(Perm.SUPPLIER_UPLOAD_VIEW)),
) -> StreamingResponse:
    content, filename = _service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/export")
def export_suppliers(
    q: str | None = Query(None),
    is_enabled: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SUPPLIER_LIST_EXPORT)),
) -> StreamingResponse:
    keyword = (q or "").strip() or None
    content, filename = _service.export_excel(
        db,
        current_user=current_user,
        keyword=keyword,
        is_enabled=is_enabled,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/upload", response_model=ApiResponse[SupplierUploadResultVO])
async def upload_suppliers(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SUPPLIER_UPLOAD_UPLOAD)),
) -> ApiResponse[SupplierUploadResultVO]:
    content = await file.read()
    result = _service.process_upload(db, file_content=content, current_user=current_user)
    message = f"导入成功：新增 {result.created_count}，跳过 {result.skipped_count}"
    return ApiResponse.ok(data=result, message=message)


@router.patch("/{full_name}", response_model=ApiResponse[SupplierVO])
def update_supplier(
    full_name: str,
    dto: SupplierUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SUPPLIER_LIST_UPDATE)),
) -> ApiResponse[SupplierVO]:
    record = _service.update(db, full_name, dto, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete("/{full_name}", response_model=ApiResponse[None])
def delete_supplier(
    full_name: str,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SUPPLIER_LIST_DELETE)),
) -> ApiResponse[None]:
    _service.delete(db, full_name)
    return ApiResponse.deleted(message="删除成功")


@router.post(
    "/{full_name}/aliases",
    response_model=ApiResponse[SupplierVO],
    status_code=status.HTTP_201_CREATED,
)
def add_supplier_alias(
    full_name: str,
    dto: SupplierAliasCreateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SUPPLIER_LIST_CREATE)),
) -> ApiResponse[SupplierVO]:
    record = _service.add_alias(db, full_name, dto, current_user=current_user)
    return ApiResponse.created(data=record, message="别名已添加")


@router.delete(
    "/{full_name}/aliases/{alias}",
    response_model=ApiResponse[SupplierVO],
)
def delete_supplier_alias(
    full_name: str,
    alias: str,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SUPPLIER_LIST_UPDATE)),
) -> ApiResponse[SupplierVO]:
    record = _service.delete_alias(db, full_name, alias, current_user=current_user)
    return ApiResponse.ok(data=record, message="别名已删除")
