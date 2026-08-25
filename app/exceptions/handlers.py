"""全局异常处理器

统一处理 FastAPI 中的各种异常，转换为标准 ApiResponse 格式
"""

from typing import Union

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.exceptions.base import BusinessException
from app.utils.response import ApiResponse


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """处理 HTTPException

    注意：透传 HTTP 状态码，保持 RESTful 语义
    """
    return JSONResponse(
        status_code=exc.status_code,  # 透传原始状态码
        content=ApiResponse.fail(
            message=exc.detail,
            code=exc.status_code,
        ).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """处理 Pydantic 验证错误"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({"field": field, "error": error["msg"]})

    return JSONResponse(
        status_code=422,  # 参数校验失败保持 422
        content=ApiResponse.fail(
            message="请求参数校验失败",
            code=422,
            data=errors if errors else None,
        ).model_dump(),
    )


async def business_exception_handler(
    request: Request, exc: BusinessException
) -> JSONResponse:
    """处理业务异常

    注意：透传 HTTP 状态码
    """
    return JSONResponse(
        status_code=exc.code,  # 透传业务异常码
        content=ApiResponse.fail(
            message=exc.message,
            code=exc.code,
            data=exc.data,
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的通用异常"""
    # TODO: 添加日志记录
    return JSONResponse(
        status_code=500,  # 系统异常保持 500
        content=ApiResponse.error(
            message="系统内部错误，请稍后重试",
            code=500,
        ).model_dump(),
    )