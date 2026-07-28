"""
钢价政策业务服务
- 管理事务（commit / rollback）
- 执行应用层业务校验（唯一约束、阶梯区间重叠）
- 提供阶梯匹配逻辑（全程 Decimal 比较）
"""

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.steel_price_policy import SteelPricePolicy, SteelPriceLadderItem
from app.parsers.steel_price_policy import parse_steel_price_policy_excel
from app.repositories.steel_price_policy import SteelPricePolicyRepository
from app.schemas.steel_price_policy import (
    LadderItemCreate,
    LadderItemUpdate,
    LadderItemResponse,
    MatchedLadderItem,
    PolicyCreate,
    PolicyDetailResponse,
    PolicyListResponse,
    PolicyMatchRequest,
    PolicyMatchResponse,
    PolicyOptionsResponse,
    PolicyQuery,
    PolicyUpdate,
    PolicyType,
)


logger = logging.getLogger("service.steel_price_policy")


def _item_left(item: LadderItemCreate) -> Decimal:
    """区间的最大左边界（用于重叠检测）。"""
    return item.min_val if item.min_val is not None else Decimal("-999999")


def _item_right(item: LadderItemCreate) -> Decimal:
    """区间的最小右边界（用于重叠检测）。"""
    return item.max_val if item.max_val is not None else Decimal("999999")


def _validate_overlapping_items(items: list[LadderItemCreate]) -> Optional[str]:
    """
    检查明细列表是否存在区间重叠冲突或间隙。

    1. 重叠检测（仅限闭区间端点）：
       < 和 > 排除边界，<= 和 >= 包含边界。
       两条相邻闭区间 [0.50, 1.00] 与 [1.00, 2.00] 存在重叠（1.00 在两者中）。

    2. 间隙检测：
       仅当 A 的真实右边界 < B 的真实左边界时构成间隙。

    3. 等价区间排除：
       min/max/operator 完全相同的两条明细（如 sort_order 优先级测试场景）
       不触发间隙检测。

    示例：
    - [0.50, 1.00) 与 [1.00, 2.00] 无间隙（相邻，1.00 不同时在两者中）
    - [0.50, 1.00] 与 [1.00, 2.00] 有重叠（1.00 同时在两者中）→ 被拒绝
    - [0.50, 2.00) 与 [0.50, 2.00) 等价 → 不触发间隙检测（支持 sort_order 测试）
    """
    import math
    eps = Decimal("1e-9")

    for i, a in enumerate(items):
        for j, b in enumerate(items):
            if j <= i:
                continue

            # 无界端点跳过（无法精确判断）
            if a.max_val is None or b.max_val is None:
                continue

            # 等价区间不视为间隙（用于 sort_order 优先级测试）
            if (
                a.min_val == b.min_val
                and a.max_val == b.max_val
                and a.min_operator == b.min_operator
                and a.max_operator == b.max_operator
            ):
                continue

            a_real_right = (
                a.max_val
                if (a.max_operator and a.max_operator.value in (">=", "<="))
                else (a.max_val - eps)
            )
            b_real_left = (
                b.min_val
                if (b.min_operator and b.min_operator.value in (">=", "<="))
                else (b.min_val + eps)
            )

            # 重叠：A 的真实右边界 >= B 的真实左边界
            if a_real_right >= b_real_left:
                return (
                    f"阶梯明细 {i + 1} 和 {j + 1} 存在重叠区间 "
                    f"({a.min_val} - {a.max_val} 与 {b.min_val} - {b.max_val})"
                )

    return None


def _item_matches(item: SteelPriceLadderItem, target_value: Decimal, target_sub_group: Optional[str]) -> bool:
    """
    判断单条明细是否命中 target_value。
    操作符仅支持 ">=", ">", "<=", "<" 四种，均为 Decimal 比较。
    当 target_sub_group 不为空时，明细的 target_sub_group 必须完全匹配。
    """
    # 子分组条件：明细有值时必须匹配请求值
    if item.target_sub_group and target_sub_group:
        if item.target_sub_group != target_sub_group:
            return False
    elif item.target_sub_group and not target_sub_group:
        return False

    def _op(val: Optional[Decimal], operator: Optional[str]) -> bool:
        if val is None or operator is None:
            return True
        if operator == ">=":
            return target_value >= val
        if operator == ">":
            return target_value > val
        if operator == "<=":
            return target_value <= val
        if operator == "<":
            return target_value < val
        return True

    return _op(item.min_val, item.min_operator) and _op(item.max_val, item.max_operator)


class SteelPricePolicyService:
    """钢价政策业务服务。"""

    def __init__(self) -> None:
        self.repository = SteelPricePolicyRepository()

    # ---- 分页列表 ----

    def paginate(
        self, db: Session, query: PolicyQuery
    ) -> tuple[list[dict[str, Any]], int, PolicyOptionsResponse]:
        skip = (query.page - 1) * query.size
        records, total = self.repository.paginate(
            db,
            year=query.year,
            month=query.month,
            steel_mill=query.steel_mill.strip() if query.steel_mill else None,
            category_name=query.category_name.strip() if query.category_name else None,
            policy_type=query.policy_type.value if query.policy_type else None,
            grade_name=query.grade_name.strip() if query.grade_name else None,
            skip=skip,
            limit=query.size,
        )
        rows = []
        for record in records:
            item_count = len(record.items)
            rows.append(
                PolicyListResponse(
                    id=record.id,
                    year=record.year,
                    month=record.month,
                    steel_mill=record.steel_mill,
                    category_name=record.category_name,
                    policy_type=record.policy_type,
                    grade_name=record.grade_name,
                    base_thickness=record.base_thickness,
                    item_count=item_count,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                ).model_dump()
            )
        options = self.repository.get_filter_options(db)
        options_resp = PolicyOptionsResponse(**options)
        return rows, total, options_resp

    # ---- 详情 ----

    def get_by_id(self, db: Session, policy_id: int) -> Optional[dict[str, Any]]:
        record = self.repository.get_by_id(db, policy_id)
        if record is None:
            return None
        sorted_items = sorted(record.items, key=lambda x: (x.sort_order, x.id))
        return PolicyDetailResponse(
            id=record.id,
            year=record.year,
            month=record.month,
            steel_mill=record.steel_mill,
            category_name=record.category_name,
            policy_type=record.policy_type,
            grade_name=record.grade_name,
            base_thickness=record.base_thickness,
            items=[
                LadderItemResponse.model_validate(item).model_dump()
                for item in sorted_items
            ],
            created_at=record.created_at,
            updated_at=record.updated_at,
        ).model_dump()

    # ---- 创建（原子含明细） ----

    def create(
        self, db: Session, data: PolicyCreate
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        payload = data.model_dump()

        # 应用层唯一键检查（兜底 DB 唯一约束）
        if self.repository.policy_exists_with_key(
            db,
            year=payload["year"],
            month=payload["month"],
            steel_mill=payload["steel_mill"],
            category_name=payload["category_name"],
            policy_type=payload["policy_type"],
            grade_name=payload.get("grade_name"),
            base_thickness=payload.get("base_thickness"),
        ):
            db.rollback()
            return None, (
                f"该年度({payload['year']})、月份({payload['month']})、钢厂({payload['steel_mill']})、"
                f"大类({payload['category_name']})、类型({payload['policy_type']})的政策已存在"
            )

        # 阶梯明细区间重叠检查
        raw_items: list[dict[str, Any]] = payload.pop("items")
        ladder_errors = _validate_overlapping_items(
            [LadderItemCreate(**item) for item in raw_items]
        )
        if ladder_errors:
            db.rollback()
            return None, f"阶梯明细校验失败：{ladder_errors}"

        try:
            policy_record = self.repository.create_policy(db, payload)
            items_data = []
            for item_d in raw_items:
                item_d = dict(item_d)
                if "min_operator" in item_d and item_d["min_operator"] is not None:
                    item_d["min_operator"] = item_d["min_operator"].value
                if "max_operator" in item_d and item_d["max_operator"] is not None:
                    item_d["max_operator"] = item_d["max_operator"].value
                items_data.append(item_d)
            self.repository.add_items(db, policy_record.id, items_data)
            db.commit()
            result = self.get_by_id(db, policy_record.id)
            return result, None
        except IntegrityError as error:
            db.rollback()
            logger.warning("创建钢价政策违反唯一约束: %s", error)
            return None, "违反业务唯一约束"
        except Exception as error:
            db.rollback()
            logger.exception("创建钢价政策失败: %s", error)
            return None, str(error)

    # ---- 更新政策头 ----

    def update(
        self, db: Session, policy_id: int, data: PolicyUpdate
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        existing = self.repository.get_by_id_unsafe(db, policy_id)
        if existing is None:
            db.rollback()
            return None, "记录不存在"

        update_data = data.model_dump(exclude_unset=True)

        # 阶梯明细整组替换（items 可能为空列表，表示清空明细）
        has_items = "items" in update_data
        raw_items: list[dict[str, Any]] | None = update_data.pop("items", None)

        if has_items and raw_items is not None and len(raw_items) > 0:
            ladder_errors = _validate_overlapping_items(
                [LadderItemCreate(**item) for item in raw_items]
            )
            if ladder_errors:
                db.rollback()
                return None, f"阶梯明细校验失败：{ladder_errors}"
            items_data = [
                {**item_d, **{
                    k: (v.value if k in ("min_operator", "max_operator") and v is not None else v)
                    for k, v in item_d.items()
                }}
                for item_d in raw_items
            ]
        elif has_items:
            items_data = []  # 空数组 = 清空明细
        else:
            items_data = None  # 未传 items

        if not update_data and items_data is None:
            db.rollback()
            return None, "未提供任何可更新字段"

        try:
            if update_data:
                self.repository.update_policy(db, policy_id, update_data)
            if items_data is not None:
                self.repository.replace_items(db, policy_id, items_data)
            db.commit()
            return self.get_by_id(db, policy_id), None
        except IntegrityError as error:
            db.rollback()
            logger.warning("更新钢价政策违反约束: id=%s, error=%s", policy_id, error)
            return None, "更新违反约束"
        except Exception as error:
            db.rollback()
            logger.exception("更新钢价政策失败: id=%s, error=%s", policy_id, error)
            return None, str(error)

    # ---- 删除 ----

    def delete(self, db: Session, policy_id: int) -> tuple[bool, Optional[str]]:
        try:
            success = self.repository.delete_policy(db, policy_id)
            if not success:
                db.rollback()
                return False, "记录不存在"
            db.commit()
            return True, None
        except Exception as error:
            db.rollback()
            logger.exception("删除钢价政策失败: id=%s, error=%s", policy_id, error)
            return False, str(error)

    # ---- 明细独立 CRUD ----

    def add_item(
        self, db: Session, policy_id: int, data: LadderItemCreate
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        policy = self.repository.get_by_id_unsafe(db, policy_id)
        if policy is None:
            return None, "政策不存在"

        item_data = data.model_dump()
        op_val = item_data.get("min_operator")
        if op_val is not None:
            item_data["min_operator"] = op_val.value
        op_val2 = item_data.get("max_operator")
        if op_val2 is not None:
            item_data["max_operator"] = op_val2.value

        try:
            created = self.repository.add_items(db, policy_id, [item_data])
            db.commit()
            return LadderItemResponse.model_validate(created[0]).model_dump(), None
        except Exception as error:
            db.rollback()
            logger.exception("新增阶梯明细失败: policy_id=%s, error=%s", policy_id, error)
            return None, str(error)

    def update_item(
        self, db: Session, item_id: int, data: LadderItemUpdate
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        existing = self.repository.get_item_by_id(db, item_id)
        if existing is None:
            return None, "明细不存在"

        update_data = data.model_dump(exclude_none=True)
        if "min_operator" in update_data and update_data["min_operator"] is not None:
            update_data["min_operator"] = update_data["min_operator"].value
        if "max_operator" in update_data and update_data["max_operator"] is not None:
            update_data["max_operator"] = update_data["max_operator"].value

        if not update_data:
            return None, "未提供任何可更新字段"

        try:
            updated = self.repository.update_item(db, item_id, update_data)
            db.commit()
            return LadderItemResponse.model_validate(updated).model_dump(), None
        except Exception as error:
            db.rollback()
            logger.exception("更新阶梯明细失败: item_id=%s, error=%s", item_id, error)
            return None, str(error)

    def delete_item(self, db: Session, item_id: int) -> tuple[bool, Optional[str]]:
        try:
            success = self.repository.delete_item(db, item_id)
            if not success:
                db.rollback()
                return False, "明细不存在"
            db.commit()
            return True, None
        except Exception as error:
            db.rollback()
            logger.exception("删除阶梯明细失败: item_id=%s, error=%s", item_id, error)
            return False, str(error)

    # ---- 阶梯匹配 ----

    def match(
        self, db: Session, data: PolicyMatchRequest
    ) -> PolicyMatchResponse:
        """
        根据政策维度 + 尺寸值查找匹配的阶梯明细。
        全程 Decimal 比较，命中多条时以 sort_order 升序、id 升序确定唯一结果。
        """
        candidates = self.repository.find_candidate_policies(
            db,
            year=data.year,
            month=data.month,
            steel_mill=data.steel_mill.strip(),
            category_name=data.category_name.strip(),
            policy_type=data.policy_type.value,
            grade_name=data.grade_name.strip() if data.grade_name else None,
            base_thickness=data.base_thickness,
        )

        if not candidates:
            return PolicyMatchResponse(matched=False)

        if len(candidates) > 1:
            logger.warning(
                "阶梯匹配命中多条政策: year=%s month=%s steel_mill=%s category=%s type=%s grade=%s base_t=%s",
                data.year, data.month, data.steel_mill, data.category_name,
                data.policy_type.value, data.grade_name, data.base_thickness,
            )

        all_hits: list[tuple[SteelPriceLadderItem, int]] = []
        for policy in candidates:
            for item in policy.items:
                if _item_matches(item, data.target_value, data.target_sub_group):
                    all_hits.append((item, policy.id))

        if not all_hits:
            return PolicyMatchResponse(matched=False)

        # 确定性排序：sort_order 升序、id 升序
        all_hits.sort(key=lambda x: (x[0].sort_order, x[0].id))
        best_item, best_policy_id = all_hits[0]

        return PolicyMatchResponse(
            matched=True,
            policy_id=best_policy_id,
            item=MatchedLadderItem.model_validate(best_item),
            price_adjustment=best_item.price_adjustment,
        )

    # ---- Excel 导入 ----

    def import_from_parser(
        self,
        db: Session,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
    ) -> dict[str, int]:
        """
        解析 Excel 文件（传入 year/month 参数），
        按 (year, month, steel_mill, category_name, policy_type, grade_name, base_thickness)
        业务唯一键做 upsert：
        - 键存在 → 删除旧政策及阶梯明细，插入新政政策及阶梯明细
        - 键不存在 → 直接插入
        返回 created_count / updated_count / skipped_count。
        """
        result = parse_steel_price_policy_excel(file_content, year=year, month=month)

        created = 0
        updated = 0
        skipped = 0

        for policy_data in result.policies:
            payload = policy_data.model_dump()
            payload["year"] = year
            payload["month"] = month

            # ParsedLadderItem.model_dump() 返回的已经是字符串，无需转换
            raw_items = payload.pop("items")
            norm_items = [dict(item) for item in raw_items]

            exists = self.repository.policy_exists_with_key(
                db,
                year=payload["year"],
                month=payload["month"],
                steel_mill=payload["steel_mill"],
                category_name=payload["category_name"],
                policy_type=payload["policy_type"],
                grade_name=payload.get("grade_name"),
                base_thickness=payload.get("base_thickness"),
            )

            try:
                if exists:
                    # 查找旧记录 ID 并替换（复用 find_candidate_policies）
                    old_records = self.repository.find_candidate_policies(
                        db,
                        year=payload["year"],
                        month=payload["month"],
                        steel_mill=payload["steel_mill"],
                        category_name=payload["category_name"],
                        policy_type=payload["policy_type"],
                        grade_name=payload.get("grade_name"),
                        base_thickness=payload.get("base_thickness"),
                    )
                    if old_records:
                        self.repository.delete_policy(db, old_records[0].id)
                        db.commit()
                    new_record = self.repository.create_policy(db, payload)
                    self.repository.add_items(db, new_record.id, norm_items)
                    db.commit()
                    updated += 1
                else:
                    new_record = self.repository.create_policy(db, payload)
                    self.repository.add_items(db, new_record.id, norm_items)
                    db.commit()
                    created += 1
            except Exception as error:
                db.rollback()
                logger.warning(
                    "导入政策失败 [%s]: %s - %s",
                    payload.get("steel_mill"),
                    payload.get("grade_name"),
                    error,
                )
                skipped += 1

        return {
            "created_count": created,
            "updated_count": updated,
            "skipped_count": skipped,
            "total": created + updated,
        }
