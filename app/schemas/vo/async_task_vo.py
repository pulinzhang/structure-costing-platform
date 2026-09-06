"""异步上传任务 VO — 各业务上传接口共用。"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.common.types.repository_types import AsyncTaskSnapshot


class AsyncTaskAcceptedVO(BaseModel):
    """异步上传受理响应（立即返回 task_id）"""

    task_id: str = Field(..., description="后台解析任务 ID，用于轮询进度")


class AsyncTaskProgressVO(BaseModel):
    """异步上传任务进度"""

    status: str = Field(..., description="pending | running | completed | failed")
    progress: int = Field(0, ge=0, le=100, description="进度百分比 0-100")
    msg: str = Field("", description="当前阶段说明")
    result: object | None = Field(None, description="完成后的业务结果")
    operator_id: int | None = Field(None, description="提交人用户 ID")
    operator_name: str | None = Field(None, description="提交人显示名")
    updated_at: float = Field(0, description="最近更新时间戳（秒）")

    @classmethod
    def from_snapshot(
        cls,
        task: AsyncTaskSnapshot,
        *,
        default_status: str = "pending",
        result: object | None = None,
    ) -> "AsyncTaskProgressVO":
        """从 AsyncTaskService.get_task_snapshot 组装进度 VO。"""
        updated_at_value = task.get("updated_at")
        updated_at = updated_at_value.timestamp() if isinstance(updated_at_value, datetime) else 0.0
        return cls(
            status=task.get("status") or default_status,
            progress=int(task.get("progress") or 0),
            msg=task.get("message") or "",
            result=result,
            operator_id=task.get("operator_id"),
            operator_name=task.get("operator_name"),
            updated_at=updated_at,
        )
