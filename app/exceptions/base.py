"""业务异常基类

异常体系说明：
- BusinessException: 通用业务异常（如库存不足、余额不足）
- NotFoundException: 资源不存在（404）
- ValidationException: 业务校验失败（如重复提交、数据冲突）
- PermissionException: 权限不足

使用方式：
```python
# Service 层抛出
raise NotFoundException(f"零件不存在: id={part_id}")

# 全局异常处理器统一捕获
# 转换为 ApiResponse.fail(message=str(exception))
```
"""

from typing import Optional


class BusinessException(Exception):
    """通用业务异常（如库存不足、余额不足）"""

    def __init__(
        self,
        message: str = "业务处理失败",
        code: int = 400,
    ):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundException(BusinessException):
    """资源不存在异常（对应 HTTP 404）"""

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message=message, code=404)


class ValidationException(BusinessException):
    """业务校验失败异常（如重复提交、数据冲突）"""

    def __init__(self, message: str = "数据校验失败"):
        super().__init__(message=message, code=422)


class PermissionException(BusinessException):
    """权限不足异常（对应 HTTP 403）"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(message=message, code=403)
