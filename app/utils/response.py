"""
统一响应工具
提供标准化的 API 响应格式
"""

from typing import Any, Dict
from fastapi.responses import JSONResponse


class ApiResponse:
    """统一 API 响应"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> JSONResponse:
        """
        成功响应

        Args:
            data: 响应数据
            message: 成功消息

        Returns:
            JSONResponse
        """
        return JSONResponse({
            "success": True,
            "message": message,
            "data": data,
        })

    @staticmethod
    def error(message: str = "操作失败", code: int = 400, data: Any = None) -> JSONResponse:
        """
        错误响应

        Args:
            message: 错误消息
            code: 错误码（HTTP 状态码）
            data: 附加数据

        Returns:
            JSONResponse
        """
        return JSONResponse(
            status_code=code,
            content={
                "success": False,
                "message": message,
                "data": data,
            }
        )

    @staticmethod
    def created(data: Any, message: str = "创建成功") -> JSONResponse:
        """创建成功响应"""
        return ApiResponse.success(data=data, message=message)

    @staticmethod
    def updated(data: Any, message: str = "更新成功") -> JSONResponse:
        """更新成功响应"""
        return ApiResponse.success(data=data, message=message)

    @staticmethod
    def deleted(message: str = "删除成功") -> JSONResponse:
        """删除成功响应"""
        return ApiResponse.success(message=message)

    @staticmethod
    def list_(
        data: list,
        total: int,
        page: int = 1,
        page_size: int = 20,
        message: str = "查询成功",
        filters: dict = None,
    ) -> JSONResponse:
        """
        列表响应（标准分页格式）

        Args:
            data: 数据列表
            total: 总记录数
            page: 当前页码（从 1 开始）
            page_size: 每页条数
            message: 消息
            filters: 可选，筛选下拉选项 {'vehicle_models': [...], 'versions': [...]}

        Returns:
            JSONResponse: 标准分页结构
                {
                    "success": true,
                    "message": "...",
                    "data": {
                        "list": [...],
                        "total": int,
                        "page": int,
                        "page_size": int,
                        "total_pages": int,
                        "has_next": bool,
                        "has_prev": bool,
                        "filters": {...}   # 可选
                    }
                }
        """
        page = max(page, 1)
        page_size = max(page_size, 1)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        body = {
            "success": True,
            "message": message,
            "data": {
                "list": data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
        if filters is not None:
            body["data"]["filters"] = filters
        return JSONResponse(body)
