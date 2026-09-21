"""零件详情利废开关：DTO 清洗与关开关清空来源。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import NotFoundException
from app.schemas.dto.stamping_part_dto import StampingPartOffalUpdateDTO
from app.schemas.vo.stamping_vo import StampingPartResponse
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.part.service import StampingPartService


def _user() -> UserVO:
    return UserVO(id=1, username="tester", real_name="测试员")


def test_offal_dto_strips_source() -> None:
    dto = StampingPartOffalUpdateDTO(is_offal_nested=True, offal_source="  侧围  ")
    assert dto.offal_source == "侧围"
    blank = StampingPartOffalUpdateDTO(is_offal_nested=True, offal_source="  ")
    assert blank.offal_source is None


def test_update_offal_not_found() -> None:
    service = StampingPartService()
    service.repository = MagicMock()
    service.repository.update.return_value = None
    dto = StampingPartOffalUpdateDTO(is_offal_nested=True, offal_source="侧围")
    with pytest.raises(NotFoundException):
        service.update_offal(MagicMock(), 99, dto, _user())


def test_update_offal_clears_source_when_off() -> None:
    service = StampingPartService()
    service.repository = MagicMock()
    service.repository.update.return_value = object()
    db = MagicMock()
    dto = StampingPartOffalUpdateDTO(is_offal_nested=False, offal_source="侧围")
    dummy = MagicMock()
    with patch.object(StampingPartResponse, "model_validate", return_value=dummy):
        result = service.update_offal(db, 7, dto, _user())
    assert result is dummy
    payload = service.repository.update.call_args.args[2]
    assert payload["is_offal_nested"] is False
    assert payload["offal_source"] is None
    assert payload["updated_by"] == "测试员"
    db.commit.assert_called_once()
