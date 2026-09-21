"""全局异常处理器

统一处理 FastAPI 中的各种异常，转换为标准 ApiResponse 格式
"""

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.common.operation_log.context import set_request_error_message
from app.common.operation_log.error_message import (
    GENERIC_PUBLIC_ERROR,
    VALIDATION_FAIL_PREFIX,
    http_exception_error_message,
    parse_validation_errors,
)
from app.exceptions.base import BusinessException
from app.utils.response import ApiResponse


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTPException

    注意：透传 HTTP 状态码，保持 RESTful 语义
    """
    audit = http_exception_error_message(exc.detail)
    set_request_error_message(request, audit)
    fail_message = exc.detail if isinstance(exc.detail, str) else audit
    return JSONResponse(
        status_code=exc.status_code,  # 透传原始状态码
        content=ApiResponse.fail(
            message=fail_message,
            code=exc.status_code,
        ).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | ValidationError
) -> JSONResponse:
    """处理 Pydantic 验证错误"""
    items, audit = parse_validation_errors(exc.errors())
    set_request_error_message(request, audit)

    return JSONResponse(
        status_code=422,  # 参数校验失败保持 422
        content=ApiResponse.fail(
            message=VALIDATION_FAIL_PREFIX,
            code=422,
            data=items if items else None,
        ).model_dump(),
    )


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    """处理业务异常

    注意：透传 HTTP 状态码
    """
    set_request_error_message(request, exc.message)
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
    set_request_error_message(request, GENERIC_PUBLIC_ERROR)
    return JSONResponse(
        status_code=500,  # 系统异常保持 500
        content=ApiResponse.error(
            message=GENERIC_PUBLIC_ERROR,
            code=500,
        ).model_dump(),
    )
