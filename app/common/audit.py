"""操作人审计字段工具（创建人 / 修改人）。

教学约定：
- 除登录外，每个路由签名必须有 current_user: UserVO = Depends(get_current_user)
- 写操作（create/update）：再以 current_user= 传给 Service
- 读/列表/删除：注入 current_user 做鉴权即可，不必传给 Service
- Service 用本模块生成 created_by / updated_by
"""

from __future__ import annotations

from typing import Any

from app.schemas.vo.user_vo import UserVO


def display_name(user: Any) -> str:
    """展示名：真实姓名优先，否则用户名（UserVO / ORM 行均可）。"""
    username = getattr(user, "username", None) or ""
    real_name = getattr(user, "real_name", None)
    return (real_name or username or "").strip() or str(username)


# 无登录上下文时的系统用户（首次 seed、本地脚本）
SYSTEM_USER = UserVO(id=0, username="system", real_name="系统", is_admin=True, permissions=["*"])

# 业务审核状态（钢材价 / 加工费 / 零件核价等共用）
AUDIT_PENDING = "pending"
AUDIT_APPROVED = "approved"
AUDIT_REJECTED = "rejected"


def audit_create(current_user: UserVO) -> dict[str, Any]:
    """新建记录时写入创建人 + 修改人。"""
    name = display_name(current_user)
    return {
        "created_by": name,
        "updated_by": name,
    }


def audit_update(current_user: UserVO) -> dict[str, Any]:
    """更新记录时写入修改人。"""
    return {
        "updated_by": display_name(current_user),
    }
