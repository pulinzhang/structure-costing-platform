"""
工程变更落库（指挥家第三步）。

职责边界：把管线结果落成可回滚档案——写变更单（含 excel_row）、回填
effect_links.change_order_id 与 upload_log_id、标上传日志 success，并 commit。
失败则 rollback 后 mark failed。
禁止：再种树或再插工艺/布点（那是 pipeline 已 flush 的内容）。
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update, display_name
from app.exceptions.base import BusinessException
from app.repositories.engineering_change.change_order_repository import (
    EngineeringChangeOrderInsert,
    EngineeringChangeOrderRepository,
)
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkRepository,
)
from app.repositories.engineering_change.upload_log_repository import (
    EngineeringChangeUploadLogRepository,
    EngineeringChangeUploadLogUpdate,
)
from app.schemas.vo.engineering_change_vo import EngineeringChangeUploadResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.upload.orchestrator.types import (
    PipelineBundle,
    PreparedBundle,
    ProgressCallback,
    report_progress,
)

logger = logging.getLogger("service.engineering_change.persist")


def persist_engineering_change_result(
    db: Session,
    prepared: PreparedBundle,
    pipeline: PipelineBundle,
    *,
    current_user: UserVO,
    on_progress: ProgressCallback | None = None,
) -> EngineeringChangeUploadResultVO:
    log_repo = EngineeringChangeUploadLogRepository()
    change_order_repo = EngineeringChangeOrderRepository()
    effect_repo = EngineeringChangeEffectLinkRepository()
    try:
        audit = audit_create(current_user)
        change_order_rows = []
        for item in prepared.change_orders:
            change_order = item.change_order
            change_order_rows.append(
                change_order_repo.create(
                    db,
                    EngineeringChangeOrderInsert(
                        upload_log_id=prepared.log_id,
                        upload_file_id=prepared.upload_file_id,
                        excel_row=change_order.excel_row,
                        project_code=change_order.project_code,
                        effective_period_text=change_order.effective_period_text,
                        change_type=change_order.change_type,
                        before_assembly_part_number=change_order.before_assembly_part_number,
                        after_assembly_part_number=change_order.after_assembly_part_number,
                        assembly_name=change_order.assembly_name,
                        part_level=change_order.part_level,
                        before_part_number=change_order.before_part_number,
                        after_part_number=change_order.after_part_number,
                        part_name=change_order.part_name,
                        seq_no=item.before_seq_no,
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                    ),
                )
            )
        if not pipeline.effect_links:
            raise BusinessException("写入成功但缺效果链接，禁止标成功")
        for link in pipeline.effect_links:
            index = link.change_order_id
            if index < 0 or index >= len(change_order_rows):
                raise BusinessException("效果链接变更单下标无效")
            link.change_order_id = change_order_rows[index].id
            link.upload_log_id = prepared.log_id
        effect_repo.bulk_create(db, pipeline.effect_links)
        log_row = log_repo.get_by_id(db, prepared.log_id)
        if log_row is None:
            raise BusinessException("上传日志不存在")
        log_repo.update(
            db,
            log_row,
            EngineeringChangeUploadLogUpdate(
                status="success",
                message=None,
                process_inserted_count=pipeline.process_inserted_count,
                die_inserted_count=pipeline.die_inserted_count,
                procurement_object_inserted_count=pipeline.procurement_inserted_count,
                welding_breakdown_inserted_count=pipeline.breakdown_inserted_count,
                not_install_count=pipeline.not_install_count,
                has_bom_assembly=pipeline.has_bom_assembly,
                customer_name=prepared.customer_name,
                updated_by=audit_update(current_user)["updated_by"],
            ),
        )
        db.commit()
    except BusinessException as error:
        db.rollback()
        mark_engineering_change_failed(db, prepared.log_id, str(error), current_user)
        raise
    except IntegrityError:
        db.rollback()
        logger.exception("工程变更落库冲突")
        mark_engineering_change_failed(db, prepared.log_id, "数据冲突，请重试", current_user)
        raise BusinessException("数据冲突，请重试") from None
    except Exception:
        db.rollback()
        logger.exception("工程变更落库失败")
        mark_engineering_change_failed(db, prepared.log_id, "工程变更落库异常", current_user)
        raise

    report_progress(on_progress, 100, "写入完成")
    first = prepared.change_orders[0]
    return EngineeringChangeUploadResultVO(
        log_id=prepared.log_id,
        change_order_ids=[row.id for row in change_order_rows],
        change_type=first.change_order.change_type,
        before_assembly_part_number=first.change_order.before_assembly_part_number,
        after_assembly_part_number=first.change_order.after_assembly_part_number,
        seq_no=first.before_seq_no,
        process_inserted_count=pipeline.process_inserted_count,
        die_inserted_count=pipeline.die_inserted_count,
        procurement_object_inserted_count=pipeline.procurement_inserted_count,
        welding_breakdown_inserted_count=pipeline.breakdown_inserted_count,
        not_install_count=pipeline.not_install_count,
        warnings=pipeline.warnings,
    )


def mark_engineering_change_failed(
    db: Session,
    log_id: int,
    message: str,
    current_user: UserVO,
) -> None:
    log_repo = EngineeringChangeUploadLogRepository()
    row = log_repo.get_by_id(db, log_id)
    if row is None:
        return
    try:
        log_repo.update(
            db,
            row,
            EngineeringChangeUploadLogUpdate(
                status="failed",
                message=message[:2000],
                updated_by=display_name(current_user),
            ),
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("回写工程变更失败状态失败 log_id=%s", log_id)
