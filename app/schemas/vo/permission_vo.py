"""权限树节点 VO"""

from pydantic import BaseModel, Field


class PermissionNodeVO(BaseModel):
    """权限目录树节点"""

    code: str
    label: str
    type: str = Field(description="group | menu | op")
    mandatory: bool = False
    children: list["PermissionNodeVO"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


PermissionNodeVO.model_rebuild()
