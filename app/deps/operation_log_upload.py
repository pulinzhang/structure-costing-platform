"""操作日志：在路由读 UploadFile 之前缓存 multipart 文件名。"""

from __future__ import annotations

from starlette.requests import Request

from app.common.operation_log.context import set_request_upload_filenames
from app.common.operation_log.upload_filename import collect_audit_upload_filenames


async def capture_upload_filenames(request: Request) -> None:
    """全局依赖：multipart 上传把文件名挂到 request.state。"""
    content_type = request.headers.get("content-type") or ""
    if "multipart/form-data" not in content_type.lower():
        return
    form = await request.form()
    names = collect_audit_upload_filenames(request.url.path, form.multi_items())
    if names:
        set_request_upload_filenames(request, names)
