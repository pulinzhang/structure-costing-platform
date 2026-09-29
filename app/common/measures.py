"""物理量换算。吨/公斤、百分/千分、毫米体积到公斤或吨，名字分开，不互相借用。"""

from decimal import Decimal

KG_PER_TON = Decimal("1000")
PERCENT = Decimal("100")
PERMILLE = Decimal("1000")
# 长×宽×厚（mm）× 密度（g/cm³）→ kg
MM3_G_PER_CM3_TO_KG = Decimal("1000000")
# 长×宽×高（mm）× 掏空系数 × 密度（g/cm³）→ 吨
MM3_G_PER_CM3_TO_TON = Decimal("1000000000")
