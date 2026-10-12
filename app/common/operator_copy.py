"""各切片过程报告共用的操作员句子。切片自己的过程仍写在本切片 messages 里。"""

from app.exceptions.base import BusinessException

OPERATOR_CALC_INTERRUPTED = "计算中断了。请再算一次。如果还是不行，把开始时间告诉维护人员。"
OPERATOR_BREAKDOWN_INTERRUPTED = "拆解中断了。请再拆一次。如果还是不行，把开始时间告诉维护人员。"


def operator_failure_text(
    error: BaseException,
    *,
    interrupted: str = OPERATOR_CALC_INTERRUPTED,
) -> str:
    """业务拒绝沿用原句。其余异常不把原文给操作员。"""
    if isinstance(error, BusinessException):
        message = error.message.strip()
        if message:
            return message
    return interrupted
