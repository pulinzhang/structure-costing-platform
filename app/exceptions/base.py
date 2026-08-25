"""业务异常基类

异常体系说明（架构宪法 §5.2）：
- BusinessException: 通用业务拒绝（默认 HTTP 400；唯一键、审核锁、缺字段；冲突传 code=409）
- NotFoundException: 资源不存在或任务过期（404）
- ValidationException: 不要用；请求体校验走 Pydantic 422；业务拒绝用 BusinessException
- PermissionException: 权限不足（403；通常由 require_perm 抛）

Service 对 Router 抛这些异常，由全局 handler 转成 ApiResponse.fail。
禁止 return None, "错误文案"；禁止 Router 再转 HTTPException。

```python
raise NotFoundException(f"零件不存在: id={part_id}")
```
"""


class BusinessException(Exception):
    """业务拒绝。默认 HTTP 400；期别冲突传 code=409。handler 按 self.code 写状态码。"""

    def __init__(
        self,
        message: str = "业务处理失败",
        code: int = 400,
        data: object | None = None,
    ):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


class NotFoundException(BusinessException):
    """资源不存在或任务过期（HTTP 404）。"""

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message=message, code=404)


class ValidationException(BusinessException):
    """不要用。请求体校验走 Pydantic 422；业务拒绝用 BusinessException（400）。"""

    def __init__(self, message: str = "数据校验失败"):
        super().__init__(message=message, code=422)


class PermissionException(BusinessException):
    """权限不足异常（对应 HTTP 403）"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(message=message, code=403)
