"""
冲压工艺 Repository（兼容入口）

实现已拆至：
- base.BaseRepository
- stamping_part_repository.StampingPartRepository
- stamping_process_repository.StampingProcessRepository
"""

from app.repositories.stamping.base import BaseRepository
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.repositories.stamping.stamping_process_repository import (
    StampingProcessRepository,
)

__all__ = [
    "BaseRepository",
    "StampingPartRepository",
    "StampingProcessRepository",
]
