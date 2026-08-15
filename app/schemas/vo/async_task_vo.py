"""异步上传任务 VO — 各业务上传接口共用。"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class AsyncTaskAcceptedVO(BaseModel):
    """异步上传受理响应（立即返回 task_id）"""

    task_id: str = Field(..., description="后台解析任务 ID，用于轮询进度")


class AsyncTaskProgressVO(BaseModel):
    """异步上传任务进度"""

    status: str = Field(..., description="pending | running | completed | failed")
    progress: int = Field(0, ge=0, le=100, description="进度百分比 0-100")
    msg: str = Field("", description="当前阶段说明")
    result: Optional[Any] = Field(None, description="完成后的业务结果")
    operator_id: Optional[int] = Field(None, description="提交人用户 ID")
    operator_name: Optional[str] = Field(None, description="提交人显示名")
    updated_at: float = Field(0, description="最近更新时间戳（秒）")

    @classmethod
    def from_snapshot(
        cls,
        task: dict[str, Any],
        *,
        default_status: str = "pending",
        result: Any = None,
    ) -> "AsyncTaskProgressVO":
        """从 AsyncTaskService.get_task_snapshot 组装进度 VO。"""
        updated_at_value = task.get("updated_at")
        if updated_at_value is None:
            updated_at = 0.0
        elif hasattr(updated_at_value, "timestamp"):
            updated_at = float(updated_at_value.timestamp())
        else:
            updated_at = float(updated_at_value)
        return cls(
            status=task.get("status") or default_status,
            progress=int(task.get("progress") or 0),
            msg=task.get("message") or "",
            result=result,
            operator_id=task.get("operator_id"),
            operator_name=task.get("operator_name"),
            updated_at=updated_at,
        )
