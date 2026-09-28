"""API 文档入口的 HTTP Basic 鉴权。账号密码只读配置。"""

import base64
import binascii
import secrets

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

_DOC_PATHS = frozenset({"/docs", "/redoc", "/openapi.json"})


def _unauthorized() -> Response:
    return Response(
        content="API 文档需要登录",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="API docs"'},
        media_type="text/plain; charset=utf-8",
    )


def _is_docs_entry(path: str) -> bool:
    normalized = path if path == "/" else path.rstrip("/")
    return normalized in _DOC_PATHS or path.startswith("/docs/")


def _credentials_match(authorization: str | None) -> bool:
    username = settings.SWAGGER_USERNAME.strip()
    password = settings.SWAGGER_PASSWORD
    if not username or not password or authorization is None:
        return False
    scheme, _, encoded = authorization.partition(" ")
    if scheme.lower() != "basic" or not encoded.strip():
        return False
    try:
        decoded = base64.b64decode(encoded.strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False
    given_username, separator, given_password = decoded.partition(":")
    if separator != ":":
        return False
    username_ok = secrets.compare_digest(given_username, username)
    password_ok = secrets.compare_digest(given_password, password)
    return username_ok and password_ok


class DocsAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not _is_docs_entry(request.url.path):
            return await call_next(request)
        if not _credentials_match(request.headers.get("Authorization")):
            return _unauthorized()
        return await call_next(request)
