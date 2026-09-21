"""
钢价政策阶梯匹配编排
- 查候选政策 + LadderMatcher 命中收集
- grade_value 精确未命中时 fallback 到通用政策
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.repositories.yishiyiyi.policy.steel_price_policy_repository import (
    MatchFilter,
    SteelPricePolicyRepository,
)
from app.schemas.dto.steel_price_policy_dto import PolicyMatchRequest
from app.schemas.vo.steel_price_policy_vo import (
    MatchedLadderItem as MatchedLadderItemVO,
)
from app.schemas.vo.steel_price_policy_vo import (
    PolicyMatchResponse,
)
from app.services.yishiyiyi.policy.match.ladder_matcher import LadderMatcher

logger = logging.getLogger("service.steel_price_policy.match")


class SteelPricePolicyMatchService:
    """钢价政策阶梯匹配。"""

    def __init__(self) -> None:
        self.repository = SteelPricePolicyRepository()
        self._matcher = LadderMatcher()

    def match(self, db: Session, data: PolicyMatchRequest) -> PolicyMatchResponse:
        """
        根据政策维度 + 尺寸值查找匹配的阶梯明细。
        全程 Decimal 比较，命中多条时以 sort_order 升序、id 升序确定唯一结果。

        Fallback 逻辑：
        - 优先精确匹配（grade_value 完全匹配）
        - 未命中时 fallback 到 grade_value 为 NULL 的通用政策
        - 这解决了马钢 Excel 中多个钢种共用同一行价格的问题
        """
        match_filter = MatchFilter(
            year=data.year,
            month=data.month,
            steel_mill=data.steel_mill.strip(),
            category_name=data.category_name.strip(),
            policy_type=data.policy_type.value,
            grade_type=data.grade_type.value if data.grade_type else None,
            grade_value=data.grade_value.strip() if data.grade_value else None,
            base_thickness=data.base_thickness,
        )

        # 尝试精确匹配
        candidates = self.repository.find_candidate_policies(db, match_filter)

        all_hits = self._matcher.collect_hits(candidates, data)

        # Fallback: grade_value 为 NULL 的通用政策
        fallback_hit = None
        if not all_hits and data.grade_value:
            fallback_filter = MatchFilter(
                year=data.year,
                month=data.month,
                steel_mill=data.steel_mill.strip(),
                category_name=data.category_name.strip(),
                policy_type=data.policy_type.value,
                grade_type=None,  # 通用政策
                grade_value=None,
                base_thickness=data.base_thickness,
            )
            fallback_candidates = self.repository.find_candidate_policies(db, fallback_filter)
            fallback_hits = self._matcher.collect_hits(fallback_candidates, data)
            if fallback_hits:
                fallback_hit = fallback_hits[0]
                logger.info(
                    "钢种 %s 无精确政策，fallback 到通用政策: policy_id=%s item_id=%s",
                    data.grade_value,
                    fallback_hit[1],
                    fallback_hit[0].id,
                )

        if not all_hits and not fallback_hit:
            return PolicyMatchResponse(matched=False)

        # 选择最佳匹配
        if fallback_hit:
            best_item, best_policy_id = fallback_hit
        else:
            if len(candidates) > 1:
                logger.warning(
                    "阶梯匹配命中多条政策: year=%s month=%s steel_mill=%s "
                    "category=%s type=%s grade=%s base_t=%s",
                    data.year,
                    data.month,
                    data.steel_mill,
                    data.category_name,
                    data.policy_type.value,
                    data.grade_value,
                    data.base_thickness,
                )
            sorted_hits = self._matcher.sort_hits(all_hits)
            best_item, best_policy_id = sorted_hits[0]

        return PolicyMatchResponse(
            matched=True,
            policy_id=best_policy_id,
            item=MatchedLadderItemVO.model_validate(best_item),
            price_adjustment=best_item.price_adjustment,
        )
