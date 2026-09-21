"""批量审核 / 删除结果的计数基类；范围字段留在各切片 VO。"""

from pydantic import BaseModel


class BatchAuditCountsVO(BaseModel):
    updated_count: int = 0
    skipped_count: int = 0
    message: str = ""


class BatchDeleteCountsVO(BaseModel):
    deleted_count: int = 0
    skipped_approved_count: int = 0


def batch_approve_message(updated_count: int, skipped_count: int) -> str:
    message = f"已审核通过 {updated_count} 条"
    if skipped_count:
        message += f"，跳过已审核 {skipped_count} 条"
    return message


def batch_reverse_message(updated_count: int, skipped_count: int) -> str:
    message = f"已反审核 {updated_count} 条"
    if skipped_count:
        message += f"，跳过非已审 {skipped_count} 条"
    return message
