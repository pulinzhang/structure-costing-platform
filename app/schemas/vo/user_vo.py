"""用户 VO - 响应数据"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.timezone import datetime_to_iso


class UserVO(BaseModel):
    """用户信息（不含密码）"""

    id: int
    username: str
    real_name: str | None = None
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    avatar: str | None = None
    is_active: bool = True
    is_admin: bool = False
    permissions: list[str] = []
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = ConfigDict(from_attributes=True)


class LoginVO(BaseModel):
    """登录成功响应"""

    token: str
    user: UserVO


class LoginKeyVO(BaseModel):
    """一次性登录公钥。私钥不下发。"""

    key_id: str
    public_key_spki: str


class AvatarUploadVO(BaseModel):
    """头像上传结果：相对路径 URL，如 /uploads/avatars/xxx.png"""

    url: str
    message: str = ""
