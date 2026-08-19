"""
钢价政策 Excel 导入服务
- 上传校验
- 解析 + 事务内批量写入（键存在则替换）
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.common.audit import AuditCreateFields, audit_create
from app.parsers.yishiyiyi.policy import parse_steel_price_policy_excel
from app.parsers.yishiyiyi.policy.models.ladder_item import ParsedLadderItem
from app.parsers.yishiyiyi.policy.models.policy import ParsedPolicy
from app.repositories.yishiyiyi.policy import SteelPricePolicyRepository
from app.repositories.yishiyiyi.policy.steel_price_policy_repository import MatchFilter
from app.schemas.dto.steel_price_policy_dto import (
    SteelPriceLadderItemWrite,
    SteelPricePolicyWrite,
)
from app.schemas.vo.steel_price_policy_vo import ImportResultResponse
from app.schemas.vo.user_vo import UserVO
from app.utils.steel_price_archive import FILE_KIND_POLICY, save_steel_price_upload

# progress_callback(progress: int, msg: str)
ProgressCallback = Callable[[int, str], None]

logger = logging.getLogger("service.steel_price_policy.import")


def _policy_write_from_parsed(
    policy: ParsedPolicy,
    *,
    year: int,
    month: int,
    audit: AuditCreateFields,
) -> SteelPricePolicyWrite:
    return SteelPricePolicyWrite(
        year=year,
        month=month,
        steel_mill=policy.steel_mill,
        category_name=policy.category_name,
        policy_type=policy.policy_type,
        grade_type=policy.grade_type,
        grade_value=policy.grade_value,
        base_thickness=policy.base_thickness,
        excel_filename=policy.excel_filename,
        created_by=audit["created_by"],
        updated_by=audit["updated_by"],
    )


def _ladder_write_from_parsed(
    item: ParsedLadderItem,
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
        is_base=1 if item.is_base else 0,
        sort_order=item.sort_order,
        excel_row=item.excel_row,
        excel_col=item.excel_col,
        created_by=audit["created_by"],
        updated_by=audit["updated_by"],
    )


class SteelPricePolicyImportService:
    """钢价政策 Excel 导入。"""

    def __init__(self) -> None:
        self.repository = SteelPricePolicyRepository()

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
        current_user: UserVO,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ImportResultResponse:
        """
        解析 Excel 文件并批量导入。
        整个导入过程在单一事务中完成，要么全部成功，要么全部失败。
        进度写入辅助库，不受本事务写锁影响。

        导入策略：
        - 键存在 → 删除旧政策及阶梯明细，插入新政政策及阶梯明细
        - 键不存在 → 直接插入

        导入前先按年度/月份归档源文件，便于与基准价文件成对核对。
        """
        create_audit = audit_create(current_user)

        def _report(progress: int, msg: str) -> None:
            if progress_callback:
                progress_callback(progress, msg)

        _report(1, "正在归档上传源文件...")
        save_steel_price_upload(
            file_content=file_content,
            filename=filename,
            year=year,
            month=month,
            file_kind=FILE_KIND_POLICY,
        )

        result = parse_steel_price_policy_excel(
            file_content,
            year=year,
            month=month,
            excel_filename=filename,
            progress_callback=progress_callback,
        )

        created = 0
        updated = 0
        policies = result.policies
        total_policies = len(policies) or 1

        try:
            for index, policy_data in enumerate(policies):
                # 写入阶段占用 70% ~ 98%
                write_progress = 70 + int((index / total_policies) * 28)
                _report(
                    write_progress,
                    f"正在写入数据库（{index + 1}/{len(policies)}）...",
                )

                policy_write = _policy_write_from_parsed(
                    policy_data,
                    year=year,
                    month=month,
                    audit=create_audit,
                )
                norm_items = [
                    _ladder_write_from_parsed(item, create_audit)
                    for item in policy_data.items
                ]

                match_filter = MatchFilter(
                    year=policy_write.year,
                    month=policy_write.month,
                    steel_mill=policy_write.steel_mill,
                    category_name=policy_write.category_name,
                    policy_type=policy_write.policy_type,
                    grade_type=policy_write.grade_type,
                    grade_value=policy_write.grade_value,
                    base_thickness=policy_write.base_thickness,
                )
                old_id = self.repository.get_policy_id_by_key(db, match_filter)

                if old_id:
                    # 替换旧政策（先删后插在同一事务中）
                    self.repository.delete_policy(db, old_id)
                    db.flush()  # 确保删除生效，避免唯一约束冲突
                    new_record = self.repository.create_policy(db, policy_write)
                    db.flush()  # 生成主键 ID
                    self.repository.add_items(db, new_record.id, norm_items)

                    logger.info(
                        "导入替换政策: steel_mill=%s grade_value=%s old_id=%s new_id=%s",
                        policy_write.steel_mill,
                        policy_write.grade_value,
                        old_id,
                        new_record.id,
                    )
                    updated += 1
                else:
                    new_record = self.repository.create_policy(db, policy_write)
                    db.flush()  # 生成主键 ID
                    self.repository.add_items(db, new_record.id, norm_items)

                    logger.info(
                        "导入创建政策: steel_mill=%s grade_value=%s id=%s",
                        policy_write.steel_mill,
                        policy_write.grade_value,
                        new_record.id,
                    )
                    created += 1

            # 整个循环完成后统一提交
            _report(99, "正在提交事务...")
            db.commit()

            logger.info(
                "导入完成: created=%d updated=%d total=%d",
                created,
                updated,
                created + updated,
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
                created,
                updated,
                error,
            )
            raise
