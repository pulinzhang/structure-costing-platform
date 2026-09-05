"""计算报告导出文件名。"""

import re

from app.common.timezone import now
from app.schemas.vo.assembly_cost_vo import AssemblyCostCalcLogVO


def safe_filename_token(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip(" ._")
    return cleaned or "报告"


def build_calc_report_filename(log: AssemblyCostCalcLogVO) -> str:
    period = f"{log.year}-{log.month:02d}"
    stamp = now().strftime("%Y%m%d_%H%M%S")
    return (
        f"总成核价计算报告_{safe_filename_token(log.location)}"
        f"_{safe_filename_token(log.vehicle_model)}_{period}_{stamp}.xlsx"
    )
