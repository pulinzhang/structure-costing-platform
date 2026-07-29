"""
钢价政策模块测试
验证主子表 CRUD、Decimal 精度、级联删除和阶梯匹配逻辑
"""

import os
import sys
from decimal import Decimal
from typing import Generator
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 每个测试函数使用独立的内存数据库，完全隔离
TEST_DB = "sqlite:///:memory:"
_engine = create_engine(
    TEST_DB,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """每个测试用例使用独立的内存数据库会话和表结构。"""
    from app.database import Base
    Base.metadata.create_all(bind=_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture(scope="function")
def service(db: Session):
    """提供已注入测试会话的 Service 实例。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    svc = SteelPricePolicyService()
    svc.repository._db = db  # 替换为测试会话（Repository 通过 db 参数调用，无需 patch）
    return svc


# =============================================================================
# 辅助：直接使用 Repository 层测试
# =============================================================================

def test_model_tables_created(db: Session):
    """验证两张新表均已创建。"""
    from app.database import Base
    table_names = {t.name for t in Base.metadata.tables.values()}
    assert "steel_price_policies" in table_names
    assert "steel_price_ladder_items" in table_names


def test_cascade_delete(db: Session):
    """验证删除政策主表时阶梯明细自动级联删除。"""
    from app.models.steel_price_policy import SteelPricePolicy, SteelPriceLadderItem

    policy = SteelPricePolicy(
        year=2026,
        month=4,
        steel_mill="马钢",
        category_name="冷轧钢",
        policy_type="THICKNESS",
        grade_name="DC01",
        base_thickness=Decimal("1.00"),
    )
    db.add(policy)
    db.flush()

    item1 = SteelPriceLadderItem(
        policy_id=policy.id,
        thick_min=Decimal("0.50"),
        thick_max=Decimal("1.00"),
        thick_min_operator=">=",
        thick_max_operator="<",
        price_adjustment=100,
        sort_order=0,
    )
    item2 = SteelPriceLadderItem(
        policy_id=policy.id,
        thick_min=Decimal("1.00"),
        thick_max=Decimal("2.00"),
        thick_min_operator=">=",
        thick_max_operator="<",
        price_adjustment=50,
        sort_order=1,
    )
    db.add_all([item1, item2])
    db.commit()

    policy_id = policy.id
    db.delete(policy)
    db.commit()

    remaining = db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.policy_id == policy_id).all()
    assert len(remaining) == 0


def test_decimal_precision_in_insert(db: Session):
    """验证 Numeric 列正确保存 Decimal 精度（小数位不丢失）。"""
    from app.models.steel_price_policy import SteelPricePolicy, SteelPriceLadderItem

    policy = SteelPricePolicy(
        year=2026,
        month=4,
        steel_mill="宝钢",
        category_name="镀锌钢",
        policy_type="WIDTH",
    )
    db.add(policy)
    db.flush()

    item = SteelPriceLadderItem(
        policy_id=policy.id,
        width_min=Decimal("0.10"),
        width_max=Decimal("1000.00"),
        width_min_operator=">=",
        width_max_operator="<",
        price_adjustment=-50,
        sort_order=0,
    )
    db.add(item)
    db.commit()

    loaded = db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.id == item.id).first()
    assert loaded.width_min == Decimal("0.10")
    assert loaded.width_max == Decimal("1000.00")
    assert loaded.price_adjustment == -50
    assert isinstance(loaded.price_adjustment, int)


def test_service_create_and_get(db: Session):
    """验证原子创建政策并通过 ID 查询。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType, Operator

    svc = SteelPricePolicyService()

    policy_data = PolicyCreate(
        year=2026,
        month=5,
        steel_mill="宝钢",
        category_name="冷轧钢",
        policy_type=PolicyType.THICKNESS,
        grade_name="DC03",
        base_thickness=Decimal("1.50"),
        items=[
            LadderItemCreate(
                thick_min=Decimal("0.50"),
                thick_min_operator=">=",
                thick_max=Decimal("1.00"),
                thick_max_operator="<",
                price_adjustment=200,
                sort_order=0,
            ),
        ],
    )

    record, error = svc.create(db, policy_data)
    assert error is None
    assert record is not None
    assert record["year"] == 2026
    assert record["grade_name"] == "DC03"
    assert len(record["items"]) == 1

    detail = svc.get_by_id(db, record["id"])
    assert detail is not None
    assert detail["month"] == 5
    assert detail["items"][0]["price_adjustment"] == 200


def test_service_create_duplicate_rejected(db: Session):
    """验证重复政策头被应用层检查拒绝。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType

    svc = SteelPricePolicyService()

    policy_data = PolicyCreate(
        year=2026,
        month=6,
        steel_mill="马钢",
        category_name="冷轧钢",
        policy_type=PolicyType.WIDTH,
        items=[
            LadderItemCreate(width_min=Decimal("1000"), width_max=Decimal("1500"), width_min_operator=">=", width_max_operator="<", price_adjustment=0, sort_order=0),
        ],
    )

    record1, err1 = svc.create(db, policy_data)
    assert err1 is None

    record2, err2 = svc.create(db, policy_data)
    assert err2 is not None
    assert "政策已存在" in err2


def test_service_delete_not_found(db: Session):
    """验证删除不存在的政策返回错误。"""
    from app.services.steel_price_policy import SteelPricePolicyService

    svc = SteelPricePolicyService()
    success, error = svc.delete(db, 99999)
    assert success is False
    assert "记录不存在" in error


def test_service_update_not_found(db: Session):
    """验证更新不存在的政策返回错误。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyUpdate

    svc = SteelPricePolicyService()
    record, error = svc.update(db, 99999, PolicyUpdate())
    assert record is None
    assert "记录不存在" in error


def test_service_ladder_overlap_rejected(db: Session):
    """验证阶梯明细区间重叠被拒绝。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType, Operator

    svc = SteelPricePolicyService()

    policy_data = PolicyCreate(
        year=2026,
        month=7,
        steel_mill="宝钢",
        category_name="冷轧钢",
        policy_type=PolicyType.THICKNESS,
        grade_name="DC01",
        base_thickness=Decimal("1.00"),
        items=[
            LadderItemCreate(
                min_val=Decimal("0.50"),
                min_operator=Operator.GTE,
                max_val=Decimal("1.50"),
                max_operator=Operator.LTE,
                price_adjustment=100,
                sort_order=0,
            ),
            LadderItemCreate(
                min_val=Decimal("1.00"),
                min_operator=Operator.GTE,
                max_val=Decimal("2.00"),
                max_operator=Operator.LTE,
                price_adjustment=50,
                sort_order=1,
            ),
        ],
    )

    record, error = svc.create(db, policy_data)
    assert error is not None
    assert "重叠区间" in error


def test_service_ladder_valid_adjacent_allowed(db: Session):
    """验证相邻区间（不重叠）允许创建。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType, Operator

    svc = SteelPricePolicyService()

    policy_data = PolicyCreate(
        year=2026,
        month=8,
        steel_mill="宝钢",
        category_name="冷轧钢",
        policy_type=PolicyType.THICKNESS,
        grade_name="DC01",
        base_thickness=Decimal("1.00"),
        items=[
            LadderItemCreate(
                min_val=Decimal("0.50"),
                min_operator=Operator.GTE,
                max_val=Decimal("1.00"),
                max_operator=Operator.LT,
                price_adjustment=100,
                sort_order=0,
            ),
            LadderItemCreate(
                min_val=Decimal("1.00"),
                min_operator=Operator.GTE,
                max_val=Decimal("2.00"),
                max_operator=Operator.LTE,
                price_adjustment=50,
                sort_order=1,
            ),
        ],
    )

    record, error = svc.create(db, policy_data)
    assert error is None
    assert len(record["items"]) == 2


def test_service_ladder_match_exact(db: Session):
    """验证阶梯精确命中：边界值在闭区间内。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType, Operator, PolicyMatchRequest

    svc = SteelPricePolicyService()

    policy_data = PolicyCreate(
        year=2026,
        month=9,
        steel_mill="宝钢",
        category_name="镀锌钢",
        policy_type=PolicyType.THICKNESS,
        grade_name="DX51D",
        base_thickness=Decimal("1.00"),
        items=[
            LadderItemCreate(
                min_val=Decimal("0.30"),
                min_operator=Operator.GTE,
                max_val=Decimal("0.80"),
                max_operator=Operator.LT,
                price_adjustment=150,
                sort_order=0,
            ),
            LadderItemCreate(
                min_val=Decimal("0.80"),
                min_operator=Operator.GTE,
                max_val=Decimal("1.20"),
                max_operator=Operator.LTE,
                price_adjustment=100,
                sort_order=1,
            ),
            LadderItemCreate(
                min_val=Decimal("1.20"),
                min_operator=Operator.GT,
                max_val=Decimal("2.00"),
                max_operator=Operator.LTE,
                price_adjustment=50,
                sort_order=2,
            ),
        ],
    )
    record, _ = svc.create(db, policy_data)

    # 命中中间档（0.80 在闭区间内）
    match_req = PolicyMatchRequest(
        year=2026,
        month=9,
        steel_mill="宝钢",
        category_name="镀锌钢",
        policy_type=PolicyType.THICKNESS,
        grade_name="DX51D",
        base_thickness=Decimal("1.00"),
        target_value=Decimal("0.80"),
    )
    result = svc.match(db, match_req)
    assert result.matched is True
    assert result.price_adjustment == 100

    # 命中高端档（> 1.20）
    match_req.target_value = Decimal("1.50")
    result = svc.match(db, match_req)
    assert result.matched is True
    assert result.price_adjustment == 50


def test_service_ladder_match_open_boundary(db: Session):
    """验证开闭边界严格区分：< 1.0 不命中 >= 1.0。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType, Operator, PolicyMatchRequest

    svc = SteelPricePolicyService()

    policy_data = PolicyCreate(
        year=2026,
        month=10,
        steel_mill="宝钢",
        category_name="冷轧钢",
        policy_type=PolicyType.THICKNESS,
        grade_name="DC01",
        base_thickness=Decimal("1.00"),
        items=[
            LadderItemCreate(
                min_val=Decimal("1.00"),
                min_operator=Operator.GTE,
                max_val=Decimal("3.00"),
                max_operator=Operator.LT,
                price_adjustment=200,
                sort_order=0,
            ),
        ],
    )
    svc.create(db, policy_data)

    # 1.00 命中（>= 1.00）
    result = svc.match(
        db,
        PolicyMatchRequest(
            year=2026, month=10, steel_mill="宝钢", category_name="冷轧钢",
            policy_type=PolicyType.THICKNESS, grade_name="DC01",
            base_thickness=Decimal("1.00"), target_value=Decimal("1.00"),
        ),
    )
    assert result.matched is True
    assert result.price_adjustment == 200

    # 3.00 不命中（< 3.00 严格）
    result2 = svc.match(
        db,
        PolicyMatchRequest(
            year=2026, month=10, steel_mill="宝钢", category_name="冷轧钢",
            policy_type=PolicyType.THICKNESS, grade_name="DC01",
            base_thickness=Decimal("1.00"), target_value=Decimal("3.00"),
        ),
    )
    assert result2.matched is False


def test_service_ladder_match_sort_order_priority(db: Session):
    """验证命中多条时 sort_order 小的优先。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType, Operator, PolicyMatchRequest

    svc = SteelPricePolicyService()

    policy_data = PolicyCreate(
        year=2026,
        month=11,
        steel_mill="宝钢",
        category_name="冷轧钢",
        policy_type=PolicyType.THICKNESS,
        grade_name="DC01",
        base_thickness=Decimal("1.00"),
        items=[
            LadderItemCreate(
                min_val=Decimal("0.50"),
                min_operator=Operator.GTE,
                max_val=Decimal("2.00"),
                max_operator=Operator.LTE,
                price_adjustment=999,
                sort_order=5,
            ),
            LadderItemCreate(
                min_val=Decimal("0.50"),
                min_operator=Operator.GTE,
                max_val=Decimal("2.00"),
                max_operator=Operator.LTE,
                price_adjustment=100,
                sort_order=0,
            ),
        ],
    )
    svc.create(db, policy_data)

    result = svc.match(
        db,
        PolicyMatchRequest(
            year=2026, month=11, steel_mill="宝钢", category_name="冷轧钢",
            policy_type=PolicyType.THICKNESS, grade_name="DC01",
            base_thickness=Decimal("1.00"), target_value=Decimal("1.00"),
        ),
    )
    assert result.matched is True
    assert result.price_adjustment == 100  # sort_order=0 优先


def test_service_ladder_match_no_candidate(db: Session):
    """验证无候选政策时返回未命中。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyMatchRequest, PolicyType

    svc = SteelPricePolicyService()
    result = svc.match(
        db,
        PolicyMatchRequest(
            year=2026, month=12, steel_mill="不存在的钢厂",
            category_name="冷轧钢", policy_type=PolicyType.WIDTH,
            target_value=Decimal("1000"),
        ),
    )
    assert result.matched is False


def test_schema_min_val_required(db: Session):
    """验证明细至少需要一个边界的 Schema 校验。"""
    from app.schemas.steel_price_policy import LadderItemCreate

    with pytest.raises(ValueError, match="至少需要"):
        LadderItemCreate(
            min_val=None,
            max_val=None,
            price_adjustment=50,
        )


def test_schema_min_gt_max_rejected(db: Session):
    """验证下限大于上限被 Schema 拒绝。"""
    from app.schemas.steel_price_policy import LadderItemCreate, Operator

    with pytest.raises(ValueError, match="不能大于"):
        LadderItemCreate(
            min_val=Decimal("2.00"),
            min_operator=Operator.GTE,
            max_val=Decimal("1.00"),
            max_operator=Operator.LTE,
            price_adjustment=50,
        )


def test_schema_thickness_requires_base(db: Session):
    """验证 THICKNESS 政策必须提供 grade_name 和 base_thickness。"""
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType

    with pytest.raises(ValueError, match="grade_name"):
        PolicyCreate(
            year=2026, month=4, steel_mill="宝钢", category_name="冷轧钢",
            policy_type=PolicyType.THICKNESS,
            grade_name=None,
            base_thickness=Decimal("1.00"),
            items=[LadderItemCreate(min_val=Decimal("1.00"), max_val=Decimal("2.00"), price_adjustment=50)],
        )

    with pytest.raises(ValueError, match="base_thickness"):
        PolicyCreate(
            year=2026, month=4, steel_mill="宝钢", category_name="冷轧钢",
            policy_type=PolicyType.THICKNESS,
            grade_name="DC01",
            base_thickness=None,
            items=[LadderItemCreate(min_val=Decimal("1.00"), max_val=Decimal("2.00"), price_adjustment=50)],
        )


def test_schema_width_policy_base_not_required(db: Session):
    """验证 WIDTH 政策不强制要求 grade_name 和 base_thickness。"""
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType

    policy = PolicyCreate(
        year=2026, month=4, steel_mill="宝钢", category_name="镀锌钢",
        policy_type=PolicyType.WIDTH,
        grade_name=None,
        base_thickness=None,
        items=[LadderItemCreate(min_val=Decimal("1000"), max_val=Decimal("1500"), price_adjustment=0)],
    )
    assert policy.policy_type == PolicyType.WIDTH


def test_service_update_replace_items(db: Session):
    """验证整组替换阶梯明细。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType, Operator, PolicyUpdate

    svc = SteelPricePolicyService()

    record, _ = svc.create(
        db,
        PolicyCreate(
            year=2026, month=12, steel_mill="马钢", category_name="冷轧钢",
            policy_type=PolicyType.WIDTH,
            items=[
                LadderItemCreate(min_val=Decimal("1000"), max_val=Decimal("1500"), price_adjustment=0, sort_order=0),
            ],
        ),
    )

    updated, error = svc.update(
        db,
        record["id"],
        PolicyUpdate(
            items=[
                LadderItemCreate(min_val=Decimal("1500"), max_operator=Operator.GT, max_val=Decimal("2000"), price_adjustment=10, sort_order=0),
            ],
        ),
    )
    assert error is None
    assert len(updated["items"]) == 1
    assert updated["items"][0]["price_adjustment"] == 10


def test_service_add_item_standalone(db: Session):
    """验证向已有政策独立新增明细。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, Operator, PolicyType, LadderItemCreate as LC

    svc = SteelPricePolicyService()

    record, _ = svc.create(
        db,
        PolicyCreate(
            year=2027, month=1, steel_mill="宝钢", category_name="冷轧钢",
            policy_type=PolicyType.WIDTH,
            items=[LadderItemCreate(min_val=Decimal("1000"), max_val=Decimal("1200"), price_adjustment=0, sort_order=0)],
        ),
    )

    added, error = svc.add_item(
        db,
        record["id"],
        LC(min_val=Decimal("1200"), min_operator=Operator.GT, max_val=Decimal("1500"), price_adjustment=10, sort_order=1),
    )
    assert error is None
    assert added["price_adjustment"] == 10

    detail = svc.get_by_id(db, record["id"])
    assert len(detail["items"]) == 2


def test_service_delete_item_standalone(db: Session):
    """验证独立删除明细。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import Operator, PolicyCreate, LadderItemCreate, PolicyType

    svc = SteelPricePolicyService()

    record, _ = svc.create(
        db,
        PolicyCreate(
            year=2027, month=2, steel_mill="宝钢", category_name="冷轧钢",
            policy_type=PolicyType.WIDTH,
            items=[
                LadderItemCreate(min_val=Decimal("1000"), max_val=Decimal("1300"), price_adjustment=0, sort_order=0),
                LadderItemCreate(min_val=Decimal("1300"), min_operator=Operator.GT, max_val=Decimal("1600"), price_adjustment=5, sort_order=1),
            ],
        ),
    )

    item_to_delete = next(i for i in record["items"] if i["price_adjustment"] == 5)

    success, error = svc.delete_item(db, item_to_delete["id"])
    assert success is True

    detail = svc.get_by_id(db, record["id"])
    assert len(detail["items"]) == 1


def test_decimal_response_not_float(db: Session):
    """验证 API 响应中的 Decimal 字段不转为 float。"""
    from app.services.steel_price_policy import SteelPricePolicyService
    from app.schemas.steel_price_policy import PolicyCreate, LadderItemCreate, PolicyType

    svc = SteelPricePolicyService()

    record, _ = svc.create(
        db,
        PolicyCreate(
            year=2027, month=3, steel_mill="宝钢", category_name="冷轧钢",
            policy_type=PolicyType.THICKNESS,
            grade_name="DC01",
            base_thickness=Decimal("0.65"),
            items=[
                LadderItemCreate(
                    min_val=Decimal("0.60"),
                    max_val=Decimal("0.80"),
                    price_adjustment=120,
                    sort_order=0,
                ),
            ],
        ),
    )

    # 验证 base_thickness 返回为 Decimal 字符串形式（而非 float 0.65）
    assert record["base_thickness"] == "0.65" or record["base_thickness"] == Decimal("0.65")
    assert "items" in record
    item = record["items"][0]
    assert item["min_val"] == "0.60" or item["min_val"] == Decimal("0.60")
    assert isinstance(item["price_adjustment"], int)  # 整数，非 float


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
