"""用户权限 DTO"""

from pydantic import BaseModel, Field


class UserPermissionsUpdateDTO(BaseModel):
    """覆盖保存用户权限码"""

    codes: list[str] = Field(default_factory=list, description="勾选的权限码列表")
