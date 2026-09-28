"""月度智能自动核价引擎 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.deleted_count import DeletedCountVO
from app.schemas.common.page_result import PageResult
from app.schemas.dto.costing_engine_dto import CostingEngineRunCreateDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.costing_engine_vo import (
    CostingEngineReadyVO,
    CostingEngineRunListItemVO,
    CostingEngineRunVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.engine.service import CostingEngineService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/costing/engine", tags=["核价引擎 API"])

_service = CostingEngineService()


@router.get(
    "/ready",
    response_model=ApiResponse[CostingEngineReadyVO],
    summary="查询核价引擎就绪状态",
)
def get_ready(
    location: str = Query(..., min_length=1, description="生产基地"),
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COSTING_VIEW)),
) -> ApiResponse[CostingEngineReadyVO]:
    ready = _service.get_ready(db, location=location, year=year, month=month)
    return ApiResponse.ok(data=ready)


@router.post(
    "/runs",
    response_model=ApiResponse[AsyncTaskAcceptedVO],
    summary="提交核价引擎运行",
)
def start_run(
    dto: CostingEngineRunCreateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COSTING_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    accepted = _service.start_run(db, dto, current_user=current_user)
    return ApiResponse.ok(data=accepted, message="引擎任务已提交")


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
    summary="查询核价引擎任务进度",
)
def get_task_progress(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COSTING_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    progress = _service.get_task_progress(db, task_id)
    return ApiResponse.ok(data=progress)


@router.get(
    "/runs/{run_id:int}",
    response_model=ApiResponse[CostingEngineRunVO],
    summary="查看核价引擎运行",
)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COSTING_VIEW)),
) -> ApiResponse[CostingEngineRunVO]:
    return ApiResponse.ok(data=_service.get_run(db, run_id))


@router.get(
    "/runs",
    response_model=ApiResponse[PageResult[CostingEngineRunListItemVO]],
    summary="分页查询核价引擎运行",
)
def list_runs(
    location: str | None = Query(None),
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COSTING_VIEW)),
) -> ApiResponse[PageResult[CostingEngineRunListItemVO]]:
    items, total = _service.list_runs(
        db,
        location=location,
        year=year,
        month=month,
        status=status_filter,
        page=page,
        size=size,
    )
    return ApiResponse.list_(
        items=items,
        total=total,
        page=page,
        page_size=size,
    )


@router.delete(
    "/runs",
    response_model=ApiResponse[DeletedCountVO],
    summary="删除全部核价引擎运行记录",
)
def delete_all_runs(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COSTING_DELETE)),
) -> ApiResponse[DeletedCountVO]:
    result = _service.delete_all_runs(db)
    return ApiResponse.ok(
        data=result,
        message=f"已删除 {result.deleted_count} 条引擎 Run（不撤销已写入的业务价格）",
    )


@router.delete(
    "/runs/{run_id:int}",
    response_model=ApiResponse[None],
    summary="删除一条核价引擎运行记录",
)
def delete_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COSTING_DELETE)),
) -> ApiResponse[None]:
    _service.delete_run(db, run_id)
    return ApiResponse.deleted(message="已删除引擎 Run（不撤销已写入的业务价格）")
