"""
钢材价格计算 API
触发编排 + 计算历史（含 detail_text 全过程）
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_price_dto import SteelPriceCalcDTO
from app.schemas.vo.steel_price_vo import SteelPriceCalcLogVO, SteelPriceCalcResultVO
from app.services.steel_price.calc import (
    SteelPriceCalcOrchestrator,
    SteelPriceCalcRequest,
)
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/steel-prices", tags=["钢材价格计算"])

_calc_orchestrator = SteelPriceCalcOrchestrator()


def _to_result_vo(result) -> SteelPriceCalcResultVO:
    return SteelPriceCalcResultVO(
        calc_batch_id=result.calc_batch_id,
        log_id=result.log_id,
        status=result.status,
        year=result.year,
        month=result.month,
        location=result.location,
        stamping_supplier=result.stamping_supplier,
        vehicle_model=result.vehicle_model,
        material_count=result.material_count,
        enriched_count=result.enriched_count,
        no_base_count=result.no_base_count,
        created_count=result.created_count,
        updated_count=result.updated_count,
        skipped_approved_count=result.skipped_approved_count,
        failed_count=result.failed_count,
        detail_text=result.detail_text,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )


@router.get(
    "/calc/logs",
    response_model=ApiResponse[PageResult[SteelPriceCalcLogVO]],
)
def list_calc_logs(
    year: int | None = Query(None, ge=2000, le=2100, description="核价年度"),
    month: int | None = Query(None, ge=1, le=12, description="核价月份"),
    location: str | None = Query(None, description="生产基地"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
) -> ApiResponse[PageResult[SteelPriceCalcLogVO]]:
    """分页查询钢价计算历史（含 detail_text）。"""
    records, total = _calc_orchestrator.list_logs(
        db,
        year=year,
        month=month,
        location=location,
        page=page,
        size=size,
    )
    return ApiResponse.list_(
        items=records,
        total=total,
        page=page,
        page_size=size,
    )


@router.get(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[SteelPriceCalcLogVO],
)
def get_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceCalcLogVO]:
    """查看单次计算全过程（detail_text）。"""
    record = _calc_orchestrator.get_log(db, log_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计算记录不存在")
    return ApiResponse.ok(data=record)


@router.post(
    "/calc",
    response_model=ApiResponse[SteelPriceCalcResultVO],
)
def calculate_steel_prices(
    body: SteelPriceCalcDTO,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceCalcResultVO]:
    """
    按筛选条件批量计算钢材联动价格并落库。

    过程与错误写入 steel_price_calc_logs.detail_text。
    """
    try:
        result = _calc_orchestrator.calculate(
            db,
            SteelPriceCalcRequest(
                year=body.year,
                month=body.month,
                location=body.location,
                stamping_supplier=body.stamping_supplier,
                vehicle_model=body.vehicle_model,
            ),
        )
        return ApiResponse.ok(data=_to_result_vo(result), message="钢价计算完成")
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"钢价计算失败: {error}",
        ) from error
