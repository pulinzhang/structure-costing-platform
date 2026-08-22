# 异常与风险分析铁律（C11）— 必须无条件遵守

## 何时必须出「异常与风险」专节

只要 Context JSON 中出现以下任一线索，报告必须有独立二级标题「异常与风险」（或同等含义），不得并进「一切正常」的叙述里：

- `missingPriceRisk.partial_count` > 0，或 `sample` 非空
- `monthOverview.partial_count` > 0
- 明细行 `status` / `calc_status` 为 `partial` 或其他非 `ok`
- `missing_leaf_count` > 0
- `meta.hasData` = false
- 存在 `engine_gate_digest` / 门禁缺口类字段
- `mom_comparison` 中后端已给出的异常涨跌标记（若有）

## 专节应写什么

1. **事实**：用 JSON 中的计数与零件号样本（最多列 Pack 已给的样本，勿编造零件号）。
2. **影响**：说明哪些结论不可当「已定稿交付底数」（例如 partial 的 `grand_total` 可能不完整）。
3. **动作**：可执行建议（催供应商报价、补年度价、去上传主数据、重跑引擎等）；有 `navigate` 则点名页面意图。

## 无异常时

仍须保留专节，明确写类似：

> 本次 Pack 显示 partial_count=0，缺价样本为空，未见核算不全或缺价风险。

禁止因为「想让报告好看」而删除风险信息。

## 禁止

- 禁止把 `partial` 说成「已全部完成」。
- 禁止在 JSON 无证据时编造「同步失败」「钢厂违约」等异常故事。
- 禁止用「加强管理」代替可执行动作。
