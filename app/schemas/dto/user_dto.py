"""用户 DTO - 请求参数"""

from pydantic import BaseModel, Field


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
    """登录请求"""

    username: str = Field(..., min_length=1, max_length=50, description="登录账号")
    password: str = Field(..., min_length=1, max_length=64, description="登录密码")
