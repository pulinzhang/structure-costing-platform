"""废料销售价固定基地/物料清单（录入顺序）。"""

from __future__ import annotations

# 每月固定 6 行；前端矩阵列：大盘价 / 扣费 / 净价（净价由后端计算）
SCRAP_PRICE_LOCATIONS: tuple[str, ...] = (
    "芜湖",
    "大连",
    "鄂尔多斯",
    "青岛",
    "福州",
    "铝板",
)

SCRAP_PRICE_LOCATION_COUNT = len(SCRAP_PRICE_LOCATIONS)
