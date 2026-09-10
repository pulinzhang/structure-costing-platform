"""分析算法版本（Snapshot.meta.analysis_version）。"""

ANALYSIS_VERSION = "v1.0"

DEFAULT_DRIVER_TOP_N = 5
ANOMALY_RATE_THRESHOLD = "0.15"
# 总成核价「单价 vs 上月」异常：绝对值 ≥ 10%
ASSEMBLY_UNIT_PRICE_MOM_THRESHOLD = "0.10"
# 总成材料行占应成本份额；一条外购件独大（如点焊胶占九成）
COMPOSITION_SHARE_THRESHOLD = "0.50"
# 有效用量过大：单价极低但行金额仍高（用量/单位可能串了）
COMPOSITION_EXTREME_QTY = "10000"
# 年度零件价：转换系数 ≥ 该值时，核价单价不得约等于采购单价（未除系数）
ANNUAL_PRICE_CONVERSION_FACTOR_MIN = "10"
# 核价单价相对「采购单价÷转换系数」允许偏差
ANNUAL_PRICE_CONVERSION_TOLERANCE = "0.10"
# 标准件 / 螺母螺栓胶块：计件核价单价通常几分钱，达到该值视为过大
STANDARD_PART_UNIT_PRICE_MAX = "1.0000"
STANDARD_PART_SUPPLY_TYPES = ("标准件", "胶块")
STANDARD_PART_NAME_KEYS = ("螺母", "螺栓", "螺钉", "螺柱", "铆钉", "胶块")
SQL_TIMEOUT_SECONDS = 5
MAX_CONCURRENT_TASKS_PER_USER = 2
