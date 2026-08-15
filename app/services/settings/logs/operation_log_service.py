"""操作日志 Service。"""

from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from typing import Any
from urllib.parse import unquote

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.operation_log.rules import (
    build_summary,
    infer_action,
    infer_module,
)
from app.common.timezone import now
from app.database import DatabaseConfig
from app.repositories.settings.logs.operation_log_repository import (
    OperationLogRepository,
)
from app.schemas.dto.operation_log_dto import OperationLogQuery
from app.schemas.vo.operation_log_vo import (
    OperationLogFilterOptionsVO,
    OperationLogVO,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.operation_log")


class OperationLogService:
    """操作审计日志业务。"""

    def __init__(self) -> None:
        self.repository = OperationLogRepository()

    def record_from_request(
        self,
        *,
        user: UserVO | None,
        method: str,
        path: str,
        query_string: str,
        status_code: int,
        client_ip: str | None,
    ) -> None:
        """中间件调用：独立 Session 写入，失败不影响主请求。"""
        session_factory = DatabaseConfig.get_session_factory()
        db = session_factory()
        try:
            action = infer_action(method, path)
            module = infer_module(path)
            summary = build_summary(method, path, action, module)
            detail = None
            if query_string:
                raw = unquote(query_string)
                # 去掉可能的 token 参数
                safe_parts = [
                    p
                    for p in raw.split("&")
                    if not p.lower().startswith(("token=", "password=", "authorization="))
                ]
                detail = "&".join(safe_parts)[:500] or None

            self.repository.create(
                db,
                {
                    "user_id": user.id if user else None,
                    "username": user.username if user else None,
                    "operator_name": display_name(user) if user else None,
                    "method": method.upper(),
                    "path": path.split("?", 1)[0][:255],
                    "module": module,
                    "action": action,
                    "summary": summary[:255],
                    "status_code": status_code,
                    "success": status_code < 400,
                    "client_ip": (client_ip or "")[:64] or None,
                    "detail": detail,
                    "created_at": now(),
                },
            )
        except Exception:
            logger.exception("写入操作日志失败: %s %s", method, path)
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    def paginate(
        self,
        db: Session,
        query: OperationLogQuery,
    ) -> tuple[list[OperationLogVO], int, OperationLogFilterOptionsVO]:
        skip = (query.page - 1) * query.size
        rows, total = self.repository.paginate(
            db,
            username=query.username,
            module=query.module,
            action=query.action,
            method=query.method,
            success=query.success,
            created_from=query.created_from,
            created_to=query.created_to,
            skip=skip,
            limit=query.size,
        )
        options = OperationLogFilterOptionsVO.model_validate(
            self.repository.list_filter_options(db)
        )
        return [OperationLogVO.model_validate(r) for r in rows], total, options

    def export(
        self,
        db: Session,
        *,
        username: str | None = None,
        module: str | None = None,
        action: str | None = None,
        method: str | None = None,
        success: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[bytes, str]:
        rows = self.repository.list_for_export(
            db,
            username=username,
            module=module,
            action=action,
            method=method,
            success=success,
            created_from=created_from,
            created_to=created_to,
        )
        wb = Workbook()
        ws = wb.active
        ws.title = "操作日志"
        headers = [
            "ID",
            "时间",
            "账号",
            "操作人",
            "模块",
            "动作",
            "方法",
            "路径",
            "摘要",
            "状态码",
            "成功",
            "IP",
            "明细",
        ]
        header_fill = PatternFill("solid", fgColor="1E1E1E")
        header_font = Font(color="FFFFFF", bold=True, size=11)
        for col, title in enumerate(headers, start=1):
            cell = ws.cell(1, col, title)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        for row_idx, row in enumerate(rows, start=2):
            created = (
                row.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if row.created_at
                else ""
            )
            values: list[Any] = [
                row.id,
                created,
                row.username or "",
                row.operator_name or "",
                row.module or "",
                row.action,
                row.method,
                row.path,
                row.summary,
                row.status_code,
                "是" if row.success else "否",
                row.client_ip or "",
                row.detail or "",
            ]
            for col, value in enumerate(values, start=1):
                ws.cell(row_idx, col, value)

        for col in ws.columns:
            max_len = 0
            letter = col[0].column_letter
            for cell in col[:200]:
                max_len = max(max_len, len(str(cell.value or "")))
            ws.column_dimensions[letter].width = min(max(max_len + 2, 10), 48)

        buffer = BytesIO()
        wb.save(buffer)
        stamp = now().strftime("%Y%m%d_%H%M%S")
        return buffer.getvalue(), f"操作日志_{stamp}.xlsx"
