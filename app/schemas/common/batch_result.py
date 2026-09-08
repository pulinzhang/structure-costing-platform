"""批量审核 / 删除结果的计数基类；范围字段留在各切片 VO。"""

from pydantic import BaseModel


class BatchAuditCountsVO(BaseModel):
    updated_count: int = 0
    skipped_count: int = 0


class BatchDeleteCountsVO(BaseModel):
    deleted_count: int = 0
    skipped_approved_count: int = 0
