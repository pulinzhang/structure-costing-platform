"""用户 DTO - 请求参数"""

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, Field


@dataclass(slots=True)
class UserInsertPayload:
    """Repository 写入用户（密码已哈希，含审计人）。"""

    username: str
    password_hash: str
    real_name: str | None = None
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    avatar: str | None = None
    is_active: bool = True
    is_admin: bool = False
    created_by: str | None = None
    updated_by: str | None = None


class UserPatchPayload(TypedDict, total=False):
    """用户部分更新（只含要改的列）。"""

    real_name: str | None
    email: str | None
    phone: str | None
    department: str | None
    avatar: str | None
    is_active: bool
    password_hash: str
    updated_by: str


class UserCreateDTO(BaseModel):
    """创建用户"""

    username: str = Field(..., min_length=2, max_length=50, description="登录账号")
    password: str = Field(..., min_length=4, max_length=64, description="登录密码")
    real_name: str | None = Field(None, max_length=50, description="姓名")
    email: str | None = Field(None, max_length=100, description="邮箱")
    phone: str | None = Field(None, max_length=20, description="电话")
    department: str | None = Field(None, max_length=50, description="部门")
    avatar: str | None = Field(None, max_length=255, description="头像路径/URL")
    is_active: bool = Field(True, description="启用状态")


class UserUpdateDTO(BaseModel):
    """更新用户（不含密码）——管理员可用"""

    real_name: str | None = Field(None, max_length=50, description="姓名")
    email: str | None = Field(None, max_length=100, description="邮箱")
    phone: str | None = Field(None, max_length=20, description="电话")
    department: str | None = Field(None, max_length=50, description="部门")
    avatar: str | None = Field(None, max_length=255, description="头像路径/URL")
    is_active: bool | None = Field(None, description="启用状态")


class UserSelfUpdateDTO(BaseModel):
    """当前用户自行更新资料（不可改账号/启用状态）"""

    real_name: str | None = Field(None, max_length=50, description="姓名")
    email: str | None = Field(None, max_length=100, description="邮箱")
    phone: str | None = Field(None, max_length=20, description="电话")
    department: str | None = Field(None, max_length=50, description="部门")


class UserPasswordUpdateDTO(BaseModel):
    """管理员重置密码（无需旧密码）"""

    password: str = Field(..., min_length=4, max_length=64, description="新密码")


class UserSelfPasswordUpdateDTO(BaseModel):
    """当前用户自行修改密码（必须验证旧密码）"""

    old_password: str = Field(..., min_length=1, max_length=64, description="当前密码")
    password: str = Field(..., min_length=6, max_length=64, description="新密码")
    logout_other_sessions: bool = Field(
        True,
        description="改密成功后是否注销其他设备登录",
    )


class UserQueryDTO(BaseModel):
    """用户分页查询"""

    keyword: str | None = Field(None, description="融合搜索（账号或姓名，模糊 OR）")
    username: str | None = Field(None, description="登录账号（模糊）")
    real_name: str | None = Field(None, description="姓名（模糊）")
    is_active: bool | None = Field(None, description="启用状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页条数")


class UserLoginDTO(BaseModel):
    """登录请求。密码是一次性公钥加密后的 Base64，不再接收明文。"""

    username: str = Field(..., min_length=1, max_length=50, description="登录账号")
    key_id: str = Field(..., min_length=16, max_length=64, description="一次性钥匙编号")
    password_cipher: str = Field(
        ..., min_length=1, max_length=2048, description="RSA-OAEP 密文 Base64"
    )


@dataclass(slots=True)
class UserTokenCreate:
    """登录会话写入。"""

    token: str
    user_id: int
    username: str
    last_active_at: datetime
    created_at: datetime
    created_by: str
    updated_by: str
    real_name: str | None = None
    email: str | None = None
    department: str | None = None
    avatar: str | None = None


class UserTokenSnapshot(TypedDict):
    """资料变更后同步到会话表的展示字段。"""

    username: str
    real_name: str | None
    email: str | None
    department: str | None
    avatar: str | None
