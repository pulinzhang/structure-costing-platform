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
    updated_at: float = Field(0, description="最近更新时间戳（秒）")
