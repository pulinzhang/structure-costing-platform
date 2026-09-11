"""全局异常处理器注册。"""

from typing import cast

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.types import ExceptionHandler

from app.exceptions.base import BusinessException
from app.exceptions.handlers import (
    business_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, cast(ExceptionHandler, http_exception_handler))
    app.add_exception_handler(
        RequestValidationError, cast(ExceptionHandler, validation_exception_handler)
    )
    app.add_exception_handler(BusinessException, cast(ExceptionHandler, business_exception_handler))
    app.add_exception_handler(Exception, cast(ExceptionHandler, generic_exception_handler))
