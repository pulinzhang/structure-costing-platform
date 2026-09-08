from app.schemas.common.batch_result import BatchAuditCountsVO, BatchDeleteCountsVO
from app.schemas.common.deleted_count import DeletedCountVO
from app.schemas.common.page_result import PageResult

# 别名，方便使用
BasePageResponse = PageResult

__all__ = [
    "BasePageResponse",
    "BatchAuditCountsVO",
    "BatchDeleteCountsVO",
    "DeletedCountVO",
    "PageResult",
]
