"""
钢材价格计算 API
触发编排（异步任务）+ 计算历史（含 detail_text 全过程）
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common import DeletedCountVO, PageResult
from app.schemas.dto.steel_price_dto import SteelPriceCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.steel_price_vo import SteelPriceCalcLogVO, SteelPriceCalcResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_PENDING,
    TASK_TYPE_STEEL_PRICE_CALC,
    AsyncTaskService,
)
from app.services.costing.steel_price.calc import (
    SteelPriceCalcOrchestrator,
)
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/costing/steel-price", tags=["钢材价格计算"])

_calc_orchestrator = SteelPriceCalcOrchestrator()
_async_task_service = AsyncTaskService()


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
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_VIEW)),
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
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_VIEW)),
) -> ApiResponse[SteelPriceCalcLogVO]:
    """查看单次计算全过程（detail_text）。"""
    record = _calc_orchestrator.get_log(db, log_id)
    return ApiResponse.ok(data=record)


@router.delete(
    "/calc/logs",
    response_model=ApiResponse[DeletedCountVO],
)
def delete_all_calc_logs(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_DELETE)),
) -> ApiResponse[DeletedCountVO]:
    result = _calc_orchestrator.delete_all_logs(db)
    return ApiResponse.ok(data=result, message=f"已删除 {result.deleted_count} 条")


@router.delete(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[None],
)
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_DELETE)),
) -> ApiResponse[None]:
    """删除一条计算历史日志（不影响已落库的钢材价格结果）。"""
    _calc_orchestrator.delete_log(db, log_id)
    return ApiResponse.deleted(message="删除成功")


@router.get(
    "/calc/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_steel_price_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询钢价计算任务进度。"""
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_STEEL_PRICE_CALC)

    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = SteelPriceCalcResultVO.model_validate(result_raw) if result_raw else None
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )


@router.post(
    "/calc",
    response_model=ApiResponse[AsyncTaskAcceptedVO],
)
def calculate_steel_prices(
    body: SteelPriceCalcDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """
    按筛选条件提交钢价联动计算（异步）。

    同一年度+月份+基地若已有 processing，直接拒绝重复提交。
    立即返回 task_id，前端轮询 /calc/tasks/{task_id} 获取进度。
    """
    accepted = _calc_orchestrator.start_calc(db, body, current_user=current_user)

    return ApiResponse.ok(
        data=accepted,
        message="已提交后台计算",
    )
