"""
钢价政策 CRUD 服务
- 主表 / 明细增删改查
- 条件批量删除、筛选统计
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.repositories.yishiyiyi.policy import SteelPricePolicyRepository
from app.repositories.yishiyiyi.policy.steel_price_policy_repository import (
    MatchFilter,
    PolicyFilter,
)
from app.schemas.dto.steel_price_policy_dto import (
    LadderItemCreate,
    LadderItemUpdate,
    PolicyCreate,
    PolicyQuery,
    PolicyUpdate,
)
from app.schemas.vo.steel_price_policy_vo import (
    LadderItemResponse,
    PolicyDetailResponse,
    PolicyListResponse,
    PolicyOptionsResponse,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.steel_price_policy.crud")


class SteelPricePolicyCrudService:
    """钢价政策主表与阶梯明细 CRUD。"""

    def __init__(self) -> None:
        self.repository = SteelPricePolicyRepository()

    def paginate(
        self, db: Session, query: PolicyQuery
    ) -> tuple[list[PolicyListResponse], int, PolicyOptionsResponse]:
        policy_filter = PolicyFilter(
            year=query.year,
            month=query.month,
            steel_mill=query.steel_mill.strip() if query.steel_mill else None,
            category_name=query.category_name.strip() if query.category_name else None,
            policy_type=query.policy_type.value if query.policy_type else None,
            grade_value=query.grade_value.strip() if query.grade_value else None,
            grade_type=query.grade_type.value if query.grade_type else None,
            skip=(query.page - 1) * query.size,
            limit=query.size,
        )
        records, total = self.repository.paginate(db, policy_filter)

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
                    grade_type=record.grade_type,
                    grade_value=record.grade_value,
                    base_thickness=record.base_thickness,
                    item_count=item_count,
                    created_by=getattr(record, "created_by", None),
                    updated_by=getattr(record, "updated_by", None),
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )
        filter_options = self.repository.get_filter_options(db)
        options_resp = PolicyOptionsResponse(
            years=filter_options.years,
            months=filter_options.months,
            steel_mills=filter_options.steel_mills,
            category_names=filter_options.category_names,
            policy_types=filter_options.policy_types,
            grade_types=filter_options.grade_types,
            grade_values=filter_options.grade_values,
        )
        return rows, total, options_resp

    def get_by_id(self, db: Session, policy_id: int) -> Optional[PolicyDetailResponse]:
        record = self.repository.get_by_id(db, policy_id, load_items=True)
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
            grade_type=record.grade_type,
            grade_value=record.grade_value,
            base_thickness=record.base_thickness,
            items=[
                LadderItemResponse.model_validate(item) for item in sorted_items
            ],
            created_by=getattr(record, "created_by", None),
            updated_by=getattr(record, "updated_by", None),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def create(
        self,
        db: Session,
        data: PolicyCreate,
        current_user: UserVO,
    ) -> tuple[Optional[PolicyDetailResponse], Optional[str]]:
        create_audit = audit_create(current_user)
        payload = data.model_dump()

        match_filter = MatchFilter(
            year=payload["year"],
            month=payload["month"],
            steel_mill=payload["steel_mill"],
            category_name=payload["category_name"],
            policy_type=payload["policy_type"],
            grade_type=payload.get("grade_type"),
            grade_value=payload.get("grade_value"),
            base_thickness=payload.get("base_thickness"),
        )
        if self.repository.policy_exists_with_key(db, match_filter):
            db.rollback()
            return None, (
                f"该年度({payload['year']})、月份({payload['month']})、钢厂({payload['steel_mill']})、"
                f"大类({payload['category_name']})、类型({payload['policy_type']})的政策已存在"
            )

        try:
            items_data = [{**item, **create_audit} for item in payload.pop("items", [])]
            policy_data = {k: v for k, v in payload.items() if k != "items"}
            policy_data.update(create_audit)
            policy_record = self.repository.create_policy(db, policy_data)
            db.flush()
            self.repository.add_items(db, policy_record.id, items_data)
            db.commit()

            base_t_str = (
                f"{policy_record.base_thickness:.2f}"
                if policy_record.base_thickness is not None
                else "N/A"
            )
            logger.info(
                "创建钢价政策: year=%s month=%s steel_mill=%s category=%s type=%s "
                "grade_type=%s grade_value=%s base_t=%s id=%s",
                policy_record.year,
                policy_record.month,
                policy_record.steel_mill,
                policy_record.category_name,
                policy_record.policy_type,
                policy_record.grade_type,
                policy_record.grade_value,
                base_t_str,
                policy_record.id,
            )

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

    def update(
        self,
        db: Session,
        policy_id: int,
        data: PolicyUpdate,
        current_user: UserVO,
    ) -> tuple[Optional[PolicyDetailResponse], Optional[str]]:
        existing = self.repository.get_by_id(db, policy_id, load_items=False)
        if existing is None:
            db.rollback()
            return None, "记录不存在"

        update_data = data.model_dump(exclude_unset=True)

        has_items = "items" in update_data
        raw_items: list[dict[str, Any]] | None = update_data.pop("items", None)

        if has_items and raw_items is not None and len(raw_items) > 0:
            items_data = raw_items
        elif has_items:
            items_data = []
        else:
            items_data = None

        if not update_data and items_data is None:
            db.rollback()
            return None, "未提供任何可更新字段"

        update_data.update(audit_update(current_user))
        try:
            self.repository.update_policy(db, policy_id, update_data)
            if items_data is not None:
                create_audit = audit_create(current_user)
                self.repository.replace_items(
                    db,
                    policy_id,
                    [{**item, **create_audit} for item in items_data],
                )
            db.commit()

            logger.info("更新钢价政策: id=%s", policy_id)

            return self.get_by_id(db, policy_id), None
        except IntegrityError as error:
            db.rollback()
            logger.warning("更新钢价政策违反约束: id=%s, error=%s", policy_id, error)
            return None, "更新违反约束"
        except Exception as error:
            db.rollback()
            logger.exception("更新钢价政策失败: id=%s, error=%s", policy_id, error)
            return None, str(error)

    def delete(self, db: Session, policy_id: int) -> tuple[bool, Optional[str]]:
        try:
            success = self.repository.delete_policy(db, policy_id)
            if not success:
                db.rollback()
                return False, "记录不存在"
            db.commit()

            logger.info("删除钢价政策: id=%s", policy_id)

            return True, None
        except Exception as error:
            db.rollback()
            logger.exception("删除钢价政策失败: id=%s, error=%s", policy_id, error)
            return False, str(error)

    def add_item(
        self,
        db: Session,
        policy_id: int,
        data: LadderItemCreate,
        current_user: UserVO,
    ) -> tuple[Optional[LadderItemResponse], Optional[str]]:
        policy = self.repository.get_by_id(db, policy_id, load_items=False)
        if policy is None:
            return None, "政策不存在"

        item_data = data.model_dump()
        op_val = item_data.get("min_operator")
        if op_val is not None:
            item_data["min_operator"] = op_val.value
        op_val2 = item_data.get("max_operator")
        if op_val2 is not None:
            item_data["max_operator"] = op_val2.value
        item_data.update(audit_create(current_user))

        try:
            created = self.repository.add_items(db, policy_id, [item_data])
            db.commit()

            logger.info(
                "新增阶梯明细: policy_id=%s item_id=%s", policy_id, created[0].id
            )

            return LadderItemResponse.model_validate(created[0]), None
        except Exception as error:
            db.rollback()
            logger.exception(
                "新增阶梯明细失败: policy_id=%s, error=%s", policy_id, error
            )
            return None, str(error)

    def update_item(
        self,
        db: Session,
        item_id: int,
        data: LadderItemUpdate,
        current_user: UserVO,
    ) -> tuple[Optional[LadderItemResponse], Optional[str]]:
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
        update_data.update(audit_update(current_user))

        try:
            updated = self.repository.update_item(db, item_id, update_data)
            db.commit()

            logger.info("更新阶梯明细: id=%s", item_id)

            return LadderItemResponse.model_validate(updated), None
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

            logger.info("删除阶梯明细: id=%s", item_id)

            return True, None
        except Exception as error:
            db.rollback()
            logger.exception("删除阶梯明细失败: item_id=%s, error=%s", item_id, error)
            return False, str(error)

    def count_policies(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> int:
        return self.repository.count_by_conditions(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill.strip() if steel_mill else None,
        )

    def get_filter_options(self, db: Session) -> PolicyOptionsResponse:
        filter_options = self.repository.get_filter_options(db)
        return PolicyOptionsResponse(
            years=filter_options.years,
            months=filter_options.months,
            steel_mills=filter_options.steel_mills,
            category_names=filter_options.category_names,
            policy_types=filter_options.policy_types,
            grade_types=filter_options.grade_types,
            grade_values=filter_options.grade_values,
        )

    def count_ladder_items(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        policy_type: Optional[str] = None,
    ) -> int:
        return self.repository.count_items_for_export(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill.strip() if steel_mill else None,
            policy_type=policy_type,
        )

    def delete_by_conditions(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> tuple[int, Optional[str]]:
        """
        根据条件批量删除政策。
        年度、月份必填；钢厂可选（不填则删除该年月下全部钢厂）。
        """
        if year is None or month is None:
            return 0, "年度、月份必须选择"

        mill = steel_mill.strip() if steel_mill else None

        try:
            count = self.repository.delete_by_conditions(
                db,
                year=year,
                month=month,
                steel_mill=mill,
            )
            db.commit()

            logger.info(
                "批量删除钢价政策: year=%s month=%s steel_mill=%s count=%s",
                year,
                month,
                mill or "(全部)",
                count,
            )

            return count, None
        except Exception as error:
            db.rollback()
            logger.exception(
                "批量删除钢价政策失败: year=%s month=%s steel_mill=%s error=%s",
                year,
                month,
                mill,
                error,
            )
            return 0, str(error)
