"""加减价导入：同一本 Excel 里，不同表页不能收到同一家钢厂。"""

import pytest

from app.exceptions.base import BusinessException
from app.parsers.yishiyiyi.policy.models.policy import ParsedPolicy
from app.services.masterdata.steel_mill.hit import SteelMillHit
from app.services.yishiyiyi.policy.importing.service import reject_sheets_sharing_mill


def _policy(sheet_name: str, category_name: str) -> ParsedPolicy:
    return ParsedPolicy(
        steel_mill=sheet_name,
        category_name=category_name,
        grade_type="CATEGORY",
        grade_value=category_name,
        policy_type="THICKNESS",
        sheet_name=sheet_name,
    )


def _hit(mill_id: int, full_name: str) -> SteelMillHit:
    return SteelMillHit(
        id=mill_id,
        abbreviation=full_name,
        full_name=full_name,
        is_enabled=True,
    )


def test_two_sheets_sharing_mill_are_rejected() -> None:
    magang = _hit(1, "马钢")
    policies = [_policy("马钢", "冷轧钢"), _policy("马钢(新)", "镀锌钢")]
    hits = {"马钢": magang, "马钢(新)": magang}

    with pytest.raises(BusinessException) as caught:
        reject_sheets_sharing_mill(policies, hits)

    message = str(caught.value)
    assert "表页「马钢」与「马钢(新)」都对应钢厂「马钢」" in message
    assert "本文件未写入" in message
    assert "1. 改 Excel：" in message
    assert "2. 改钢厂档案：" in message
    assert "不要让这两个表页名都指向「马钢」" in message


def test_same_sheet_many_policies_pass() -> None:
    magang = _hit(1, "马钢")
    policies = [_policy("马钢", "冷轧钢"), _policy("马钢", "镀锌钢")]
    reject_sheets_sharing_mill(policies, {"马钢": magang})


def test_different_mills_pass() -> None:
    policies = [_policy("马钢", "冷轧钢"), _policy("宝钢", "冷轧钢")]
    hits = {"马钢": _hit(1, "马钢"), "宝钢": _hit(2, "宝钢")}
    reject_sheets_sharing_mill(policies, hits)
