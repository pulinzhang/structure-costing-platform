"""年度模具费计算常量。"""

STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"

STALE_PROCESSING_SECONDS = 2 * 60 * 60
DUPLICATE_SCOPE_CALC_MESSAGE = "当前年度/基地/项目正在计算中，请勿重复提交。"
APPROVED_SCOPE_MESSAGE = "该范围已有已审核模具费，请先反审核后再计算。"
