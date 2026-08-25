"""
钢价政策 CRUD 服务
- 主表 / 明细增删改查
- 条件批量删除、筛选统计
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import AuditCreateFields, audit_create, display_name
from app.exceptions.base import BusinessException, NotFoundException
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
    SteelPriceLadderItemWrite,
    SteelPricePolicyWrite,
)
from app.schemas.vo.steel_price_policy_vo import (
    LadderItemResponse,
    PolicyDetailResponse,
    PolicyListResponse,
    PolicyOptionsResponse,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.steel_price_policy.crud")


def _ladder_write_from_create(
    item: LadderItemCreate,
    audit: AuditCreateFields,
) -> SteelPriceLadderItemWrite:
    return SteelPriceLadderItemWrite(
        target_sub_group=item.target_sub_group,
        thick_min=item.thick_min,
        thick_min_operator=item.thick_min_operator,
        thick_max=item.thick_max,
        thick_max_operator=item.thick_max_operator,
        width_min=item.width_min,
        width_min_operator=item.width_min_operator,
        width_max=item.width_max,
        width_max_operator=item.width_max_operator,
        zinc_coating_min=item.zinc_coating_min,
        zinc_coating_min_operator=item.zinc_coating_min_operator,
        zinc_coating_max=item.zinc_coating_max,
        zinc_coating_max_operator=item.zinc_coating_max_operator,
        price_adjustment=item.price_adjustment,
        is_base=item.is_base,
        sort_order=item.sort_order,
        created_by=audit["created_by"],
        updated_by=audit["updated_by"],
    )


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

    def get_by_id(self, db: Session, policy_id: int) -> PolicyDetailResponse:
        record = self.repository.get_by_id(db, policy_id, load_items=True)
        if record is None:
            raise NotFoundException("政策记录不存在")
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
            items=[LadderItemResponse.model_validate(item) for item in sorted_items],
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
    ) -> PolicyDetailResponse:
        create_audit = audit_create(current_user)
        policy_type = data.policy_type.value
        grade_type = data.grade_type.value if data.grade_type else None

        match_filter = MatchFilter(
            year=data.year,
            month=data.month,
            steel_mill=data.steel_mill,
            category_name=data.category_name,
            policy_type=policy_type,
            grade_type=grade_type,
            grade_value=data.grade_value,
            base_thickness=data.base_thickness,
        )
        if self.repository.policy_exists_with_key(db, match_filter):
            raise BusinessException(
                f"该年度({data.year})、月份({data.month})、钢厂({data.steel_mill})、"
                f"大类({data.category_name})、类型({policy_type})的政策已存在"
            )

        try:
            policy_record = self.repository.create_policy(
                db,
                SteelPricePolicyWrite(
                    year=data.year,
                    month=data.month,
                    steel_mill=data.steel_mill,
                    category_name=data.category_name,
                    policy_type=policy_type,
                    grade_type=grade_type,
                    grade_value=data.grade_value,
                    base_thickness=data.base_thickness,
                    created_by=create_audit["created_by"],
                    updated_by=create_audit["updated_by"],
                ),
            )
            db.flush()
            self.repository.add_items(
                db,
                policy_record.id,
                [_ladder_write_from_create(item, create_audit) for item in data.items],
            )
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

            return self.get_by_id(db, policy_record.id)
        except IntegrityError as error:
            db.rollback()
            logger.warning("创建钢价政策违反唯一约束: %s", error)
            raise BusinessException("违反业务唯一约束") from error
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建钢价政策失败")
            raise

    def update(
        self,
        db: Session,
        policy_id: int,
        data: PolicyUpdate,
        current_user: UserVO,
    ) -> PolicyDetailResponse:
        existing = self.repository.get_by_id(db, policy_id, load_items=False)
        if existing is None:
            raise NotFoundException("记录不存在")

        if not data.model_fields_set:
            raise BusinessException("未提供任何可更新字段")

        try:
            self.repository.update_policy(
                db,
                policy_id,
                data,
                updated_by=display_name(current_user),
            )
            if "items" in data.model_fields_set:
                create_audit = audit_create(current_user)
                self.repository.replace_items(
                    db,
                    policy_id,
                    [_ladder_write_from_create(item, create_audit) for item in (data.items or [])],
                )
            db.commit()

            logger.info("更新钢价政策: id=%s", policy_id)

            return self.get_by_id(db, policy_id)
        except IntegrityError as error:
            db.rollback()
            logger.warning("更新钢价政策违反约束: id=%s, error=%s", policy_id, error)
            raise BusinessException("更新违反约束") from error
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新钢价政策失败: id=%s", policy_id)
            raise

    def delete(self, db: Session, policy_id: int) -> None:
        try:
            success = self.repository.delete_policy(db, policy_id)
            if not success:
                db.rollback()
                raise NotFoundException("记录不存在")
            db.commit()

            logger.info("删除钢价政策: id=%s", policy_id)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除钢价政策失败: id=%s", policy_id)
            raise

    def add_item(
        self,
        db: Session,
        policy_id: int,
        data: LadderItemCreate,
        current_user: UserVO,
    ) -> LadderItemResponse:
        policy = self.repository.get_by_id(db, policy_id, load_items=False)
        if policy is None:
            raise NotFoundException("政策不存在")

        try:
            created = self.repository.add_items(
                db,
                policy_id,
                [_ladder_write_from_create(data, audit_create(current_user))],
            )
            db.commit()

            logger.info("新增阶梯明细: policy_id=%s item_id=%s", policy_id, created[0].id)

            return LadderItemResponse.model_validate(created[0])
        except Exception:
            db.rollback()
            logger.exception("新增阶梯明细失败: policy_id=%s", policy_id)
            raise

    def update_item(
        self,
        db: Session,
        item_id: int,
        data: LadderItemUpdate,
        current_user: UserVO,
    ) -> LadderItemResponse:
        existing = self.repository.get_item_by_id(db, item_id)
        if existing is None:
            raise NotFoundException("明细不存在")

        if not data.model_fields_set:
            raise BusinessException("未提供任何可更新字段")

        try:
            updated = self.repository.update_item(
                db,
                item_id,
                data,
                updated_by=display_name(current_user),
            )
            if updated is None:
                raise NotFoundException("明细不存在")
            db.commit()

            logger.info("更新阶梯明细: id=%s", item_id)

            return LadderItemResponse.model_validate(updated)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新阶梯明细失败: item_id=%s", item_id)
            raise

    def delete_item(self, db: Session, item_id: int) -> None:
        try:
            success = self.repository.delete_item(db, item_id)
            if not success:
                db.rollback()
                raise NotFoundException("明细不存在")
            db.commit()

            logger.info("删除阶梯明细: id=%s", item_id)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除阶梯明细失败: item_id=%s", item_id)
            raise

    def count_policies(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
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
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        policy_type: str | None = None,
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
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
    ) -> int:
        """
        根据条件批量删除政策。
        年度、月份必填；钢厂可选（不填则删除该年月下全部钢厂）。
        """
        if year is None or month is None:
            raise BusinessException("年度、月份必须选择")

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

            return count
        except Exception:
            db.rollback()
            logger.exception(
                "批量删除钢价政策失败: year=%s month=%s steel_mill=%s",
                year,
                month,
                mill,
            )
            raise
