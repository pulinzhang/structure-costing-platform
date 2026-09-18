"""材料清单上传：与冲压同一入队模式。"""

from __future__ import annotations

import pytest

from app.exceptions.base import BusinessException
from app.schemas.vo.user_vo import UserVO
from app.services.bom.upload.upload_service import BomUploadService


def _user() -> UserVO:
    return UserVO(id=1, username="tester", real_name="测试员")


def test_start_upload_requires_location() -> None:
    with pytest.raises(BusinessException, match="请选择采购基地"):
        BomUploadService.start_upload(
            file_content=b"fake",
            filename="a.xlsx",
            location="  ",
            vehicle_model="T13J",
            current_user=_user(),
        )


def test_start_upload_requires_vehicle_model() -> None:
    with pytest.raises(BusinessException, match="请选择项目"):
        BomUploadService.start_upload(
            file_content=b"fake",
            filename="a.xlsx",
            location="青岛",
            vehicle_model="",
            current_user=_user(),
        )


def test_start_upload_rejects_empty_file() -> None:
    with pytest.raises(BusinessException, match="文件内容为空"):
        BomUploadService.start_upload(
            file_content=b"",
            filename="a.xlsx",
            location="青岛",
            vehicle_model="T13J",
            current_user=_user(),
        )
