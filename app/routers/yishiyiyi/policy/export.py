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
from app.schemas.dto.steel_price_policy_dto import PolicyExportPreviewQuery, PolicyExportQuery
from app.schemas.vo.steel_price_policy_vo import ExportRow
from app.schemas.vo.user_vo import UserVO
from app.services.yishiyiyi.policy.steel_price_policy_service import SteelPricePolicyService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/yishiyiyi/policy", tags=["钢价政策导出"])

_policy_service = SteelPricePolicyService()


@router.get("/export")
def export_policies_excel(
    query: PolicyExportQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_DOWNLOAD_EXPORT)),
) -> StreamingResponse:
    """
    导出钢价政策主子表联合数据为 Excel。
    筛选：年度、月份、钢厂、分类、牌号。
    """
    excel_bytes, filename = _policy_service.generate_export_excel_bytes(
        db,
        year=query.year,
        month=query.month,
        steel_mill=query.steel_mill,
        category_name=query.category_name,
        grade_value=query.grade_value,
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
    query: PolicyExportPreviewQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_DOWNLOAD_VIEW)),
) -> ApiResponse[PageResult[ExportRow]]:
    """
    预览导出数据（主子表联合查询，分页）。
    筛选：年度、月份、钢厂、分类、牌号。
    """
    records = _policy_service.get_export_data(
        db,
        year=query.year,
        month=query.month,
        steel_mill=query.steel_mill,
        category_name=query.category_name,
        grade_value=query.grade_value,
        page=query.page,
        size=query.size,
    )
    total = _policy_service.count_export_data(
        db,
        year=query.year,
        month=query.month,
        steel_mill=query.steel_mill,
        category_name=query.category_name,
        grade_value=query.grade_value,
    )
    return ApiResponse.list_(items=records, total=total, page=query.page, page_size=query.size)
