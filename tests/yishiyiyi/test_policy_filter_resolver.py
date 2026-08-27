"""政策筛选：档案大类 / 牌号 → 政策 category_name 别名。"""

from app.schemas.dto.steel_grade_category_dto import SteelGradeCategoryCreate
from app.services.yishiyiyi.policy.filter_resolver import resolve_policy_category_filter
from app.services.yishiyiyi.steel_grade_category import SteelGradeCategoryService
from app.services.yishiyiyi.steel_grade_category.constants import CANONICAL_CATEGORY_NAMES
from app.schemas.vo.user_vo import UserVO


def _seed_grade(db_session, grade: str, category_name: str) -> None:
    service = SteelGradeCategoryService()
    if service.repository.get_by_grade(db_session, grade) is not None:
        return
    user = UserVO(id=1, username="tester", display_name="测试", is_admin=True, permissions=["*"])
    service.create(
        db_session,
        SteelGradeCategoryCreate(grade=grade, category_name=category_name),
        current_user=user,
    )
    db_session.commit()


def test_resolve_category_aliases_cold_rolled(db_session):
    resolved = resolve_policy_category_filter(db_session, category_name="冷轧")
    assert resolved.no_match is False
    assert resolved.policy_category_names is not None
    assert "冷轧" in resolved.policy_category_names
    assert "冷轧钢" in resolved.policy_category_names


def test_resolve_grade_to_category(db_session):
    _seed_grade(db_session, grade="POLICY_TEST_DC04", category_name="冷轧")
    resolved = resolve_policy_category_filter(db_session, grade_value="POLICY_TEST_DC04")
    assert resolved.no_match is False
    assert resolved.policy_category_names is not None
    assert "冷轧钢" in resolved.policy_category_names


def test_resolve_grade_and_category_intersection(db_session):
    _seed_grade(db_session, grade="POLICY_TEST_DC04_B", category_name="冷轧")
    resolved = resolve_policy_category_filter(
        db_session,
        category_name="冷轧",
        grade_value="POLICY_TEST_DC04_B",
    )
    assert resolved.no_match is False
    assert "冷轧" in (resolved.policy_category_names or frozenset())


def test_resolve_grade_category_mismatch(db_session):
    _seed_grade(db_session, grade="POLICY_TEST_DC04_C", category_name="冷轧")
    resolved = resolve_policy_category_filter(
        db_session,
        category_name="镀锌",
        grade_value="POLICY_TEST_DC04_C",
    )
    assert resolved.no_match is True


def test_resolve_unknown_grade(db_session):
    resolved = resolve_policy_category_filter(db_session, grade_value="UNKNOWN999")
    assert resolved.no_match is True


def test_canonical_category_names():
    assert list(CANONICAL_CATEGORY_NAMES) == ["冷轧", "镀锌", "酸洗"]
