"""上传 scope 合法性测试。"""

from __future__ import annotations

import pytest

from app.common.upload_scope_validation import (
    validate_bom_material_upload_scope,
    validate_stamping_process_upload_scope,
)
from app.exceptions.base import BusinessException


def test_validate_stamping_process_upload_scope_ok() -> None:
    scope = validate_stamping_process_upload_scope(
        location="青岛",
        stamping_supplier="样例冲压有限公司",
        vehicle_model="青岛T28",
        version="V1",
    )
    assert scope.location == "青岛"
    assert scope.stamping_supplier == "样例冲压有限公司"
    assert scope.vehicle_model == "T28"
    assert scope.version == "V1"


def test_validate_stamping_process_upload_scope_missing_fields() -> None:
    with pytest.raises(BusinessException, match="冲压工厂"):
        validate_stamping_process_upload_scope(
            location="青岛",
            stamping_supplier="",
            vehicle_model="T28",
            version="V1",
        )


def test_validate_bom_material_upload_scope_ok() -> None:
    scope = validate_bom_material_upload_scope(
        location="青岛",
        vehicle_model="青岛T28",
        bom_version="D_00",
    )
    assert scope.location == "青岛"
    assert scope.vehicle_model == "T28"
    assert scope.bom_version == "D_00"


def test_validate_bom_material_upload_scope_missing_project() -> None:
    with pytest.raises(BusinessException, match="项目"):
        validate_bom_material_upload_scope(
            location="青岛",
            vehicle_model=None,
            bom_version="D_00",
        )


def test_validate_bom_material_upload_scope_missing_version() -> None:
    with pytest.raises(BusinessException, match="版本"):
        validate_bom_material_upload_scope(
            location="青岛",
            vehicle_model="T28",
            bom_version="",
        )
