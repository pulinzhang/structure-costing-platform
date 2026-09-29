"""系统配置与档案列缺省。种子、列默认、空快照回退共用这一份。核价运行值仍从设置读取。"""

from decimal import Decimal

DEFAULT_STEEL_DENSITY = Decimal("7.85")
DEFAULT_MATERIAL_LOSS_RATE = Decimal("0.003")  # 千分之 3
DEFAULT_SCRAP_RECOVERY_RATE = Decimal("0.97")  # 97%
DEFAULT_FINISHED_FINANCE_RATE = Decimal("0.02")  # 2%
DEFAULT_FINISHED_MANAGEMENT_RATE = Decimal("0.02")  # 2%
DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE = Decimal("0.01")  # 1%
DEFAULT_FINISHED_SCRAP_RATE = Decimal("0.003")  # 千分之 3
DEFAULT_FINISHED_PRETAX_PROFIT_RATE = Decimal("0.02")  # 2%
DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON = Decimal("150")  # 元/吨
DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT = Decimal("300")  # 元/吨；极端月份再在设置里调高
DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT = Decimal("120")  # 元/吨
# 设置页加工费上限的表单上界。与月涨跌限额同值，规则不同。
MAX_BASE_PRICE_PROCESSING_FEE_LIMIT = 300
DEFAULT_BODY_PANEL_MAX_THICKNESS = Decimal("3.00")  # mm；大于此值的乘用车车身件料厚整批拒绝
DEFAULT_ALLOCATION_QTY = Decimal("10")  # 万台；检具费与模具单价共用
