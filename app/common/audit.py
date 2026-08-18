"""操作人审计字段工具（创建人 / 修改人）。

教学约定：
- 除登录外，每个路由签名必须有 current_user: UserVO = Depends(get_current_user)
- 写操作（create/update）：再以 current_user= 传给 Service
- 读/列表/删除：注入 current_user 做鉴权即可，不必传给 Service
- Service 用本模块生成 created_by / updated_by
"""

from __future__ import annotations

from typing import TypedDict

from app.schemas.vo.user_vo import UserVO


class AuditCreateFields(TypedDict):
    """新建时写入的操作人。"""

    created_by: str
    updated_by: str


class AuditUpdateFields(TypedDict):
    """更新时写入的操作人。"""

    updated_by: str


def display_name(user: object) -> str:
    """展示名：真实姓名优先，否则用户名（UserVO / ORM 行均可）。"""
    username = str(getattr(user, "username", None) or "").strip()
    real_name = str(getattr(user, "real_name", None) or "").strip()
    return real_name or username


# 无登录上下文时的系统用户（首次 seed、本地脚本）
SYSTEM_USER = UserVO(id=0, username="system", real_name="系统", is_admin=True, permissions=["*"])

# 业务审核状态（钢材价 / 加工费 / 零件核价 / 冲次单价 / 焊接单价等共用）
AUDIT_PENDING = "pending"
AUDIT_APPROVED = "approved"
AUDIT_REJECTED = "rejected"

AUDIT_STATUS_LABELS: dict[str, str] = {
    AUDIT_PENDING: "待审",
    AUDIT_APPROVED: "已通过",
    AUDIT_REJECTED: "已驳回",
}


def audit_status_label(status: str | None) -> str:
    """审核状态码 → 中文展示；未知码原样返回。"""
    if status is None:
        return ""
    return AUDIT_STATUS_LABELS.get(status, status)


def audit_create(current_user: UserVO) -> AuditCreateFields:
    """新建记录时写入创建人 + 修改人。"""
    name = display_name(current_user)
    return {
        "created_by": name,
        "updated_by": name,
    }


def audit_update(current_user: UserVO) -> AuditUpdateFields:
    """更新记录时写入修改人。"""
    return {
        "updated_by": display_name(current_user),
    }
