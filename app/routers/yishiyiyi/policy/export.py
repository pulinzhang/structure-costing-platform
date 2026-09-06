"""
钢价政策导出 API
导出 Excel + 导出预览分页。
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.vo.steel_price_policy_vo import ExportRow
from app.schemas.vo.user_vo import UserVO
from app.services.yishiyiyi.policy import SteelPricePolicyService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/yishiyiyi/policy", tags=["钢价政策导出"])

DEFAULT_PAGE_SIZE = 100

_policy_service = SteelPricePolicyService()


@router.get("/export")
def export_policies_excel(
    year: int | None = None,
    month: int | None = None,
    steel_mill: str | None = None,
    category_name: str | None = None,
    grade_value: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_DOWNLOAD_EXPORT)),
) -> StreamingResponse:
    """
    导出钢价政策主子表联合数据为 Excel，用于测试部门核对。
    """
    excel_bytes, filename = _policy_service.generate_export_excel_bytes(
        db,
        year=year,
        month=month,
        steel_mill=steel_mill,
        category_name=category_name.strip() if category_name else None,
        grade_value=grade_value.strip() if grade_value else None,
        current_user=current_user,
    )

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )


@router.get(
    "/export-preview",
    response_model=ApiResponse[PageResult[ExportRow]],
)
def export_policies_preview(
    year: int | None = None,
    month: int | None = None,
    steel_mill: str | None = None,
    category_name: str | None = None,
    grade_value: str | None = None,
    page: int = 1,
    size: int = DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_DOWNLOAD_VIEW)),
) -> ApiResponse[PageResult[ExportRow]]:
    """
    预览导出数据（主子表联合查询，分页）
    """
    category = category_name.strip() if category_name else None
    grade = grade_value.strip() if grade_value else None
    mill = steel_mill.strip() if steel_mill else None
    records = _policy_service.get_export_data(
        db,
        year=year,
        month=month,
        steel_mill=mill,
        category_name=category,
        grade_value=grade,
        page=page,
        size=size,
    )
    total = _policy_service.count_export_data(
        db,
        year=year,
        month=month,
        steel_mill=mill,
        category_name=category,
        grade_value=grade,
    )
    return ApiResponse.list_(items=records, total=total, page=page, page_size=size)
