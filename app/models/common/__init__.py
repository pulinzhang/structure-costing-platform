"""ORM 横切：审计 Mixin 等（非业务实体表）。"""

from app.models.common.audit_mixin import AuditUserMixin

__all__ = [
    "AuditUserMixin",
]
