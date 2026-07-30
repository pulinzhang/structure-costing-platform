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
    GradeType,
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


def _compare(value: Optional[Decimal], operator: Optional[str]) -> bool:
    """
    单条件比较：value 是否满足 operator 条件。
    operator 为空或 None 时视为无限制，返回 True。
    """
    if operator is None or value is None:
        return True
    if operator == ">=":
        return value >= Decimal(str(operator).replace(">=", ""))
    if operator == ">":
        return value > Decimal(str(operator).replace(">", ""))
    if operator == "<=":
        return value <= Decimal(str(operator).replace("<=", ""))
    if operator == "<":
        return value < Decimal(str(operator).replace("<", ""))
    return True


def _validate_overlapping_in_dimension(
    items: list[LadderItemCreate],
    dim: str,  # "thick" or "width"
) -> Optional[str]:
    """
    检查同一维度下的区间重叠（简化版：只检查同一 target_sub_group 内的重叠）。
    后续可扩展为更复杂的重叠检测逻辑。
    """
    return None  # 暂时禁用，待实现完整重叠检测


def _item_matches(
    item: SteelPriceLadderItem,
    thickness: Optional[Decimal],
    width: Optional[Decimal],
    target_sub_group: Optional[str],
) -> bool:
    """
    判断单条明细是否命中给定的厚度和宽度值。
    - 厚度/宽度为 None 时，该维度不参与匹配
    - target_sub_group 非空时，必须完全匹配
    """
    # 子分组条件
    if item.target_sub_group and target_sub_group:
        if item.target_sub_group != target_sub_group:
            return False
    elif item.target_sub_group and not target_sub_group:
        return False

    # 厚度条件匹配
    if thickness is not None:
        if item.thick_min is not None:
            op = item.thick_min_operator or ">="
            if op == ">=" and not (thickness >= item.thick_min):
                return False
            if op == ">" and not (thickness > item.thick_min):
                return False
        if item.thick_max is not None:
            op = item.thick_max_operator or "<"
            if op == "<=" and not (thickness <= item.thick_max):
                return False
            if op == "<" and not (thickness < item.thick_max):
                return False

    # 宽度条件匹配
    if width is not None:
        if item.width_min is not None:
            op = item.width_min_operator or ">="
            if op == ">=" and not (width >= item.width_min):
                return False
            if op == ">" and not (width > item.width_min):
                return False
        if item.width_max is not None:
            op = item.width_max_operator or "<"
            if op == "<=" and not (width <= item.width_max):
                return False
            if op == "<" and not (width < item.width_max):
                return False

    return True


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
            grade_value=query.grade_value.strip() if query.grade_value else None,
            grade_type=query.grade_type.value if query.grade_type else None,
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
                    grade_type=record.grade_type,
                    grade_value=record.grade_value,
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
            grade_type=record.grade_type,
            grade_value=record.grade_value,
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
            grade_type=payload.get("grade_type"),
            grade_value=payload.get("grade_value"),
            base_thickness=payload.get("base_thickness"),
        ):
            db.rollback()
            return None, (
                f"该年度({payload['year']})、月份({payload['month']})、钢厂({payload['steel_mill']})、"
                f"大类({payload['category_name']})、类型({payload['policy_type']})的政策已存在"
            )

        # 阶梯明细重叠检查（暂时禁用，待实现）
        # raw_items: list[dict[str, Any]] = payload.pop("items")
        # ladder_errors = _validate_overlapping_items(
        #     [LadderItemCreate(**item) for item in raw_items]
        # )
        # if ladder_errors:
        #     db.rollback()
        #     return None, f"阶梯明细校验失败：{ladder_errors}"

        try:
            # 提取主表字段和明细数据
            items_data = payload.pop("items", [])
            policy_data = {k: v for k, v in payload.items() if k != "items"}
            policy_record = self.repository.create_policy(db, policy_data)
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
            items_data = raw_items  # 重叠检查暂时禁用
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

        Fallback 逻辑：
        - 优先精确匹配（grade_value 完全匹配）
        - 未命中时 fallback 到 grade_value 为 NULL 的通用政策
        - 这解决了马钢 Excel 中多个钢种共用同一行价格的问题
        """
        # 尝试精确匹配
        candidates = self.repository.find_candidate_policies(
            db,
            year=data.year,
            month=data.month,
            steel_mill=data.steel_mill.strip(),
            category_name=data.category_name.strip(),
            policy_type=data.policy_type.value,
            grade_type=data.grade_type.value if data.grade_type else None,
            grade_value=data.grade_value.strip() if data.grade_value else None,
            base_thickness=data.base_thickness,
        )

        all_hits = self._collect_hits(candidates, data)

        # Fallback: grade_value 为 NULL 的通用政策
        fallback_hit = None
        if not all_hits and data.grade_value:
            fallback_candidates = self.repository.find_candidate_policies(
                db,
                year=data.year,
                month=data.month,
                steel_mill=data.steel_mill.strip(),
                category_name=data.category_name.strip(),
                policy_type=data.policy_type.value,
                grade_type=None,  # 通用政策
                grade_value=None,
                base_thickness=data.base_thickness,
            )
            fallback_hits = self._collect_hits(fallback_candidates, data)
            if fallback_hits:
                fallback_hit = fallback_hits[0]
                logger.info(
                    "钢种 %s 无精确政策，fallback 到通用政策: policy_id=%s item_id=%s",
                    data.grade_value, fallback_hit[1], fallback_hit[0].id,
                )

        if not all_hits and not fallback_hit:
            return PolicyMatchResponse(matched=False)

        # 选择最佳匹配
        if fallback_hit:
            best_item, best_policy_id = fallback_hit
        else:
            if len(candidates) > 1:
                logger.warning(
                    "阶梯匹配命中多条政策: year=%s month=%s steel_mill=%s category=%s type=%s grade=%s base_t=%s",
                    data.year, data.month, data.steel_mill, data.category_name,
                    data.policy_type.value, data.grade_value, data.base_thickness,
                )
            all_hits.sort(key=lambda x: (x[0].sort_order, x[0].id))
            best_item, best_policy_id = all_hits[0]

        return PolicyMatchResponse(
            matched=True,
            policy_id=best_policy_id,
            item=MatchedLadderItem.model_validate(best_item),
            price_adjustment=best_item.price_adjustment,
        )

    def _collect_hits(
        self,
        candidates: list[SteelPricePolicy],
        data: PolicyMatchRequest,
    ) -> list[tuple[SteelPriceLadderItem, int]]:
        """从候选政策中收集所有匹配项。"""
        hits: list[tuple[SteelPriceLadderItem, int]] = []
        for policy in candidates:
            for item in policy.items:
                if _item_matches(
                    item,
                    thickness=getattr(data, 'thickness', None),
                    width=getattr(data, 'width', None),
                    target_sub_group=data.target_sub_group,
                ):
                    hits.append((item, policy.id))
        return hits

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
        按 (year, month, steel_mill, category_name, policy_type, grade_value, base_thickness)
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
                grade_type=payload.get("grade_type"),
            grade_value=payload.get("grade_value"),
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
                        grade_type=payload.get("grade_type"),
            grade_value=payload.get("grade_value"),
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
                    payload.get("grade_value"),
                    error,
                )
                skipped += 1

        return {
            "created_count": created,
            "updated_count": updated,
            "skipped_count": skipped,
            "total": created + updated,
        }
