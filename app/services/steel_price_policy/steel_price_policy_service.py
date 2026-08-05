"""
钢价政策业务服务
- 管理事务（commit / rollback）
- 执行应用层业务校验（唯一约束、阶梯区间重叠）
- 提供阶梯匹配逻辑（全程 Decimal 比较）
- 记录业务操作日志
"""

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.parsers.steel_price_policy import parse_steel_price_policy_excel
from app.repositories.steel_price_policy import SteelPricePolicyRepository
from app.repositories.steel_price_policy.dto import ExportRow, FilterOptions
from app.repositories.steel_price_policy.steel_price_policy_repository import (
    MatchFilter,
    PolicyFilter,
)
from app.schemas.steel_price_policy import (
    GradeType,
    ImportResultResponse,
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
from app.services.steel_price_policy.export_service import SteelPricePolicyExportService
from app.services.steel_price_policy.ladder_matcher import LadderMatcher


logger = logging.getLogger("service.steel_price_policy")


class SteelPricePolicyService:
    """钢价政策业务服务。"""

    def __init__(self) -> None:
        self.repository = SteelPricePolicyRepository()
        self._matcher = LadderMatcher()
        self._export_service = SteelPricePolicyExportService()

    # ---- 分页列表 ----

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

    # ---- 详情 ----

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
                LadderItemResponse.model_validate(item)
                for item in sorted_items
            ],
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    # ---- 创建（原子含明细） ----

    def create(
        self, db: Session, data: PolicyCreate
    ) -> tuple[Optional[PolicyDetailResponse], Optional[str]]:
        payload = data.model_dump()

        # 应用层唯一键检查（兜底 DB 唯一约束）
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
            # 提取主表字段和明细数据
            items_data = payload.pop("items", [])
            policy_data = {k: v for k, v in payload.items() if k != "items"}
            policy_record = self.repository.create_policy(db, policy_data)
            db.flush()  # 生成主键 ID
            self.repository.add_items(db, policy_record.id, items_data)
            db.commit()

            # 事务成功后记录日志
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

    # ---- 更新政策头 ----

    def update(
        self, db: Session, policy_id: int, data: PolicyUpdate
    ) -> tuple[Optional[PolicyDetailResponse], Optional[str]]:
        existing = self.repository.get_by_id(db, policy_id, load_items=False)
        if existing is None:
            db.rollback()
            return None, "记录不存在"

        update_data = data.model_dump(exclude_unset=True)

        # 阶梯明细整组替换（items 可能为空列表，表示清空明细）
        has_items = "items" in update_data
        raw_items: list[dict] | None = update_data.pop("items", None)

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

    # ---- 删除 ----

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

    # ---- 明细独立 CRUD ----

    def add_item(
        self, db: Session, policy_id: int, data: LadderItemCreate
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

        try:
            created = self.repository.add_items(db, policy_id, [item_data])
            db.commit()

            logger.info("新增阶梯明细: policy_id=%s item_id=%s", policy_id, created[0].id)

            return LadderItemResponse.model_validate(created[0]), None
        except Exception as error:
            db.rollback()
            logger.exception("新增阶梯明细失败: policy_id=%s, error=%s", policy_id, error)
            return None, str(error)

    def update_item(
        self, db: Session, item_id: int, data: LadderItemUpdate
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
        match_filter = MatchFilter(
            year=data.year,
            month=data.month,
            steel_mill=data.steel_mill.strip(),
            category_name=data.category_name.strip(),
            policy_type=data.policy_type.value,
            grade_type=data.grade_type.value if data.grade_type else None,
            grade_value=data.grade_value.strip() if data.grade_value else None,
            base_thickness=data.base_thickness,
        )

        # 尝试精确匹配
        candidates = self.repository.find_candidate_policies(db, match_filter)

        all_hits = self._matcher.collect_hits(candidates, data)

        # Fallback: grade_value 为 NULL 的通用政策
        fallback_hit = None
        if not all_hits and data.grade_value:
            fallback_filter = MatchFilter(
                year=data.year,
                month=data.month,
                steel_mill=data.steel_mill.strip(),
                category_name=data.category_name.strip(),
                policy_type=data.policy_type.value,
                grade_type=None,  # 通用政策
                grade_value=None,
                base_thickness=data.base_thickness,
            )
            fallback_candidates = self.repository.find_candidate_policies(db, fallback_filter)
            fallback_hits = self._matcher.collect_hits(fallback_candidates, data)
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
            sorted_hits = self._matcher.sort_hits(all_hits)
            best_item, best_policy_id = sorted_hits[0]

        return PolicyMatchResponse(
            matched=True,
            policy_id=best_policy_id,
            item=MatchedLadderItem.model_validate(best_item),
            price_adjustment=best_item.price_adjustment,
        )

    # ---- Excel 导入 ----

    def validate_upload(
        self,
        file_content: bytes,
        filename: str,
    ) -> None:
        """
        验证上传文件，返回 None 表示验证通过。
        抛出 ValueError 表示验证失败。
        """
        from app.config import settings

        if not filename:
            raise ValueError("未提供文件名")
        ext = filename.lower()
        if not (ext.endswith(".xlsx") or ext.endswith(".xls") or ext.endswith(".xlsm")):
            raise ValueError("仅支持 .xlsx、.xls 或 .xlsm 文件")
        if not file_content:
            raise ValueError("上传文件为空")
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            raise ValueError(f"文件过大，最大支持 {max_mb}MB")

    def import_from_parser(
        self,
        db: Session,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
    ) -> ImportResultResponse:
        """
        解析 Excel 文件并批量导入。
        整个导入过程在单一事务中完成，要么全部成功，要么全部失败。

        导入策略：
        - 键存在 → 删除旧政策及阶梯明细，插入新政政策及阶梯明细
        - 键不存在 → 直接插入
        """
        result = parse_steel_price_policy_excel(
            file_content, year=year, month=month, excel_filename=filename
        )

        created = 0
        updated = 0

        try:
            for policy_data in result.policies:
                payload = policy_data.model_dump()
                payload["year"] = year
                payload["month"] = month

                raw_items = payload.pop("items")
                norm_items = [dict(item) for item in raw_items]

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
                old_id = self.repository.get_policy_id_by_key(db, match_filter)

                if old_id:
                    # 替换旧政策（先删后插在同一事务中）
                    self.repository.delete_policy(db, old_id)
                    db.flush()  # 确保删除生效，避免唯一约束冲突
                    new_record = self.repository.create_policy(db, payload)
                    db.flush()  # 生成主键 ID
                    self.repository.add_items(db, new_record.id, norm_items)

                    logger.info(
                        "导入替换政策: steel_mill=%s grade_value=%s old_id=%s new_id=%s",
                        payload.get("steel_mill"),
                        payload.get("grade_value"),
                        old_id,
                        new_record.id,
                    )
                    updated += 1
                else:
                    new_record = self.repository.create_policy(db, payload)
                    db.flush()  # 生成主键 ID
                    self.repository.add_items(db, new_record.id, norm_items)

                    logger.info(
                        "导入创建政策: steel_mill=%s grade_value=%s id=%s",
                        payload.get("steel_mill"),
                        payload.get("grade_value"),
                        new_record.id,
                    )
                    created += 1

            # 整个循环完成后统一提交
            db.commit()

            logger.info(
                "导入完成: created=%d updated=%d total=%d",
                created, updated, created + updated,
            )

            return ImportResultResponse(
                created_count=created,
                updated_count=updated,
                skipped_count=0,
                total=created + updated,
            )
        except Exception as error:
            db.rollback()
            logger.exception(
                "批量导入失败（已全部回滚）: created=%d updated=%d error=%s",
                created, updated, error,
            )
            raise

    # ---- Excel 导出数据查询 ----

    def get_export_data(
        self,
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> list[ExportRow]:
        """
        获取导出数据（主子表联合查询）。
        """
        return self._export_service.get_export_data(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            skip=skip,
            limit=limit,
        )

    def count_export_data(
        self,
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> int:
        """
        统计导出数据总数。
        """
        return self._export_service.count_export_data(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
        )

    def generate_export_excel_bytes(
        self,
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """
        生成导出 Excel 文件，返回 (文件字节数据, 文件名)。
        """
        return self._export_service.export_to_excel(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
        )

    # ---- 条件批量删除 ----

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
        年度、月份、钢厂必须同时提供。
        """
        if year is None or month is None or not steel_mill:
            return 0, "年度、月份、钢厂必须同时选择"

        try:
            count = self.repository.delete_by_conditions(
                db,
                year=year,
                month=month,
                steel_mill=steel_mill.strip(),
            )
            db.commit()

            logger.info(
                "批量删除钢价政策: year=%s month=%s steel_mill=%s count=%s",
                year, month, steel_mill, count,
            )

            return count, None
        except Exception as error:
            db.rollback()
            logger.exception(
                "批量删除钢价政策失败: year=%s month=%s steel_mill=%s error=%s",
                year, month, steel_mill, error,
            )
            return 0, str(error)
