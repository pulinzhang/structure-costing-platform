"""上传文件名写入操作日志上下文。"""

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.testclient import TestClient

from app.common.operation_log.context import get_request_upload_filenames
from app.deps.operation_log_upload import capture_upload_filenames


def test_capture_excel_filename_without_consuming_upload() -> None:
    app = FastAPI(dependencies=[Depends(capture_upload_filenames)])

    @app.post("/api/bom/upload")
    async def upload_bom(request: Request, file: UploadFile = File(...)) -> dict[str, object]:
        content = await file.read()
        return {
            "names": get_request_upload_filenames(request),
            "got": file.filename,
            "size": len(content),
        }

    client = TestClient(app)
    response = client.post(
        "/api/bom/upload",
        files={
            "file": (
                "料单.xlsx",
                b"excel-bytes",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["names"] == ["料单.xlsx"]
    assert body["got"] == "料单.xlsx"
    assert body["size"] == len(b"excel-bytes")
