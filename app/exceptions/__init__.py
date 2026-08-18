"""业务异常体系

统一异常类，用于 Service 层抛出业务异常，
由全局异常处理器转换为 ApiResponse.fail()
"""

from app.exceptions.base import (
    BusinessException,
    NotFoundException,
    ValidationException,
    PermissionException,
)

__all__ = [
    "BusinessException",
    "NotFoundException",
    "ValidationException",
    "PermissionException",
]
