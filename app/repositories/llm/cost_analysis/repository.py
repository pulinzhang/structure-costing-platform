"""L0 成品核价只读门面：组合四个主题仓库，自身不含 SQL。"""

from __future__ import annotations

from app.repositories.llm.cost_analysis.card import L0CardRepository
from app.repositories.llm.cost_analysis.composition import L0CompositionRepository
from app.repositories.llm.cost_analysis.monthly_totals import L0MonthlyTotalsRepository
from app.repositories.llm.cost_analysis.part_rows import L0PartRowRepository


class L0CostAnalysisRepository:
    """分析层仍调这一扇门；改 SQL 去对应主题文件，不要往本类加查询。"""

    def __init__(self) -> None:
        monthly = L0MonthlyTotalsRepository()
        parts = L0PartRowRepository()
        card = L0CardRepository()
        composition = L0CompositionRepository()
        self.query_monthly_totals = monthly.query_monthly_totals
        self.count_filtered_missing_price = monthly.count_filtered_missing_price
        self.query_part_rows = parts.query_part_rows
        self.query_latest_card_scope = card.query_latest_card_scope
        self.query_card_item_rows = card.query_card_item_rows
        self.query_item_price_rows = composition.query_item_price_rows
        self.query_composition_lines = composition.query_composition_lines
        self.query_standard_part_price_lines = composition.query_standard_part_price_lines
