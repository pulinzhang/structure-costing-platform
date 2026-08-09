from typing import Generic, TypeVar, Any, Optional
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应

    使用示例：
    ```python
    # 单个对象
    ApiResponse[UserVO]

    # 列表
    ApiResponse[list[UserVO]]

    # 分页
    ApiResponse[PageResult[UserVO]]

    # 无 data（删除成功等）
    ApiResponse[None]
    ```
    """

    code: int = 200
    success: bool = True
    message: str = "操作成功"
    data: T | None = None

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "操作成功") -> "ApiResponse[T]":
        """成功响应（2xx）

        注意：data 默认 None，允许无返回值场景（如 DELETE 成功）
        """
        return cls(code=200, success=True, message=message, data=data)

    @classmethod
    def fail(
        cls,
        message: str = "操作失败",
        code: int = 400,
        data: Any = None,
    ) -> "ApiResponse[Any]":
        """业务错误响应（4xx）

        使用场景：
        - 业务规则冲突（如库存不足、余额不足）
        - 数据冲突（如重复提交）
        - 详细校验错误信息（通过 data 参数返回）

        注意：
        - 禁止用于 HTTP 参数校验（由 RequestValidationError 处理）
        - 禁止用于资源不存在（由 HTTPException 或 NotFoundException 处理）
        - 禁止用于权限失败（由 PermissionException 处理）
        """
        return cls(code=code, success=False, message=message, data=data)

    @classmethod
    def error(
        cls,
        message: str = "系统错误",
        code: int = 500,
    ) -> "ApiResponse[None]":
        """系统错误响应（5xx）"""
        return cls(code=code, success=False, message=message, data=None)

    @classmethod
    def created(cls, data: T, message: str = "创建成功") -> "ApiResponse[T]":
        return cls(code=201, success=True, message=message, data=data)

    @classmethod
    def updated(cls, data: T, message: str = "更新成功") -> "ApiResponse[T]":
        return cls(code=200, success=True, message=message, data=data)

    @classmethod
    def deleted(cls, message: str = "删除成功") -> "ApiResponse[None]":
        return cls(code=200, success=True, message=message, data=None)

    @classmethod
    def list_(
        cls,
        items: list[Any],
        total: int,
        page: int = 1,
        page_size: int = 20,
        message: str = "查询成功",
        filters: Any = None,
    ) -> "ApiResponse[Any]":
        """分页列表响应"""
        from app.schemas.common.page_result import PageResult

        page = max(page, 1)
        page_size = max(page_size, 1)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        page_result = PageResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
            filters=filters,
        )
        return cls(code=200, success=True, message=message, data=page_result)