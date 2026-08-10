"""
设置 VO - 响应数据结构
"""

from pydantic import BaseModel


class ConfigVO(BaseModel):
    """系统配置 VO"""
    app_name: str
    version: str
