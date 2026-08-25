"""文件溯源 API。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.file_trace_dto import UploadFileListQuery
from app.schemas.vo.file_trace_vo import UploadFileFiltersVO, UploadFileVO
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.upload_file_service import UploadFileService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/file-trace", tags=["文件溯源"])
_service = UploadFileService()


@router.get("/list", response_model=ApiResponse[PageResult[UploadFileVO]])
def list_upload_files(
    query: UploadFileListQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.FILE_TRACE_VIEW)),
) -> ApiResponse[PageResult[UploadFileVO]]:
    rows, total = _service.list_files(db, query, current_user)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条记录",
    )


@router.get("/filters", response_model=ApiResponse[UploadFileFiltersVO])
def get_upload_file_filters(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.FILE_TRACE_VIEW)),
) -> ApiResponse[UploadFileFiltersVO]:
    filters = _service.get_filters(db, current_user)
    return ApiResponse.ok(data=filters)


@router.get("/{file_id}", response_model=ApiResponse[UploadFileVO])
def get_upload_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.FILE_TRACE_VIEW)),
) -> ApiResponse[UploadFileVO]:
    vo = _service.get_file(db, file_id, current_user)
    return ApiResponse.ok(data=vo)


@router.get("/{file_id}/download")
def download_upload_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.FILE_TRACE_DOWNLOAD)),
) -> FileResponse:
    absolute_path, original_filename, media_type = _service.resolve_download(
        db, file_id, current_user
    )
    encoded_name = quote(original_filename)
    return FileResponse(
        path=str(absolute_path),
        media_type=media_type,
        filename=original_filename,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )
