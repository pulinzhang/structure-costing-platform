"""HTTP 中间件注册。后添加的先执行（洋葱外层）。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.docs_auth import DocsAuthMiddleware
from app.middleware.no_cache_frontend import NoCacheFrontendMiddleware
from app.middleware.operation_log_middleware import OperationLogMiddleware
from app.middleware.request_log import RequestLogMiddleware


def register_middleware(app: FastAPI) -> None:
    # 入站：DocsAuth → RequestLog → NoCache → OperationLog → CORS → 路由
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(OperationLogMiddleware)
    app.add_middleware(NoCacheFrontendMiddleware)
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(DocsAuthMiddleware)
