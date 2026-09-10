"""操作日志 Repository。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, false, or_
from sqlalchemy.orm import Query, Session

from app.common.operation_log.ip_location import IpLocation
from app.models.settings import OperationLog
from app.repositories.persist import model_from_payload
from app.schemas.dto.operation_log_dto import OperationLogCreate


class OperationLogRepository:
    """操作日志数据访问。"""

    def create(self, db: Session, data: OperationLogCreate) -> OperationLog:
        row = model_from_payload(OperationLog, data)
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def paginate(
        self,
        db: Session,
        *,
        username: str | None = None,
        permission_code: str | None = None,
        permission_codes: list[str] | None = None,
        menu_labels: list[str] | None = None,
        login_only: bool = False,
        module: str | None = None,
        action: str | None = None,
        method: str | None = None,
        success: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[OperationLog], int]:
        q = self._filtered_query(
            db,
            username=username,
            permission_code=permission_code,
            permission_codes=permission_codes,
            menu_labels=menu_labels,
            login_only=login_only,
            module=module,
            action=action,
            method=method,
            success=success,
            created_from=created_from,
            created_to=created_to,
        )
        total = q.count()
        rows = q.order_by(OperationLog.id.desc()).offset(skip).limit(limit).all()
        return rows, total

    def list_for_export(
        self,
        db: Session,
        *,
        username: str | None = None,
        permission_code: str | None = None,
        permission_codes: list[str] | None = None,
        menu_labels: list[str] | None = None,
        login_only: bool = False,
        module: str | None = None,
        action: str | None = None,
        method: str | None = None,
        success: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 10000,
    ) -> list[OperationLog]:
        q = self._filtered_query(
            db,
            username=username,
            permission_code=permission_code,
            permission_codes=permission_codes,
            menu_labels=menu_labels,
            login_only=login_only,
            module=module,
            action=action,
            method=method,
            success=success,
            created_from=created_from,
            created_to=created_to,
        )
        return q.order_by(OperationLog.id.desc()).limit(limit).all()

    def get_ip_location(self, db: Session, client_ip: str) -> IpLocation | None:
        """同一 IP 已有归属地则复用；只读 1 行。"""
        row = (
            db.query(OperationLog.ip_country, OperationLog.ip_province, OperationLog.ip_city)
            .filter(OperationLog.client_ip == client_ip)
            .filter(
                or_(
                    OperationLog.ip_country.isnot(None),
                    OperationLog.ip_province.isnot(None),
                    OperationLog.ip_city.isnot(None),
                )
            )
            .order_by(OperationLog.id.desc())
            .limit(1)
            .first()
        )
        if row is None:
            return None
        country, province, city = row
        if not country and not province and not city:
            return None
        return {"country": country, "province": province, "city": city}

    def update_ip_location(
        self,
        db: Session,
        *,
        log_id: int,
        client_ip: str,
        country: str | None,
        province: str | None,
        city: str | None,
    ) -> None:
        """仅当 id + ip 仍匹配时回写归属地。"""
        db.query(OperationLog).filter(
            OperationLog.id == log_id,
            OperationLog.client_ip == client_ip,
        ).update(
            {
                OperationLog.ip_country: country,
                OperationLog.ip_province: province,
                OperationLog.ip_city: city,
            },
            synchronize_session=False,
        )

    def _filtered_query(
        self,
        db: Session,
        *,
        username: str | None,
        permission_code: str | None,
        permission_codes: list[str] | None,
        menu_labels: list[str] | None,
        login_only: bool,
        module: str | None,
        action: str | None,
        method: str | None,
        success: bool | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> Query[OperationLog]:
        q = db.query(OperationLog)
        if username:
            keyword = f"%{username.strip()}%"
            q = q.filter(
                or_(
                    OperationLog.username.like(keyword),
                    OperationLog.operator_name.like(keyword),
                )
            )
        if login_only:
            q = q.filter(
                or_(
                    OperationLog.action == "登录",
                    OperationLog.path == "/api/auth/login",
                )
            )
        elif permission_code:
            q = q.filter(OperationLog.permission_code == permission_code.strip())
        elif permission_codes is not None:
            if not permission_codes:
                q = q.filter(false())
            elif menu_labels:
                q = q.filter(
                    or_(
                        OperationLog.permission_code.in_(permission_codes),
                        and_(
                            OperationLog.permission_code.is_(None),
                            OperationLog.module.in_(menu_labels),
                        ),
                    )
                )
            else:
                q = q.filter(OperationLog.permission_code.in_(permission_codes))
        if module:
            q = q.filter(OperationLog.module == module.strip())
        if action:
            q = q.filter(OperationLog.action == action.strip())
        if method:
            q = q.filter(OperationLog.method == method.strip().upper())
        if success is not None:
            q = q.filter(OperationLog.success == success)
        if created_from is not None:
            q = q.filter(OperationLog.created_at >= created_from)
        if created_to is not None:
            q = q.filter(OperationLog.created_at <= created_to)
        return q
