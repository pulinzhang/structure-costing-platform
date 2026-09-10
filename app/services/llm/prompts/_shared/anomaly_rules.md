# 异常与风险（C11）— 按需说明，禁止空章灌水

## 何时写

**仅当**满足以下任一条件时，才在回答中提及异常 / 风险 / 缺价 / 算不全：

- 用户问题本身关心：缺价、算不全、风险、能不能当定稿底数、数据是否可靠等；
- 或回答所依赖的核心数字因以下情况**可能不可信**，且不说清楚会误导用户：

线索（JSON 中）：
- `missingPriceRisk.partial_count` > 0，或 `sample` 非空
- `monthOverview.partial_count` > 0
- 明细行 `status` / `calc_status` 为 `partial` 或其他非 `ok`
- `missing_leaf_count` > 0
- `meta.hasData` = false（且与用户问题相关）
- 存在 `engine_gate_digest` / 门禁缺口类字段
- **基准价探查**：`base_price_anomalies.items`（`base_price_jump`）、基准价 `trend.anomaly_months`
- **加减价探查**（口语常说「加减价」，不必写「政策」）：`policy_anomalies.items`（`policy_adjustment_jump`）、加减价 `trend.anomaly_months`
- **总成核价探查**：`risk.zero_unit_price_count` / `risks` 中 `zero_unit_price`（应成本/月总账单价为 0）；`mom_anomalies.items`（相对上月单价绝对值 ≥ 10%）；`composition_anomalies.items` / `risks` 中 `composition_dominance`（一条材料明细占应成本 ≥ 50%，或有效用量过大）；`standard_part_anomalies.items` / `risks` 中 `standard_part_high_price`（螺母、螺栓、胶块等计件单价过大，通常几分钱）
- **冲压零件核价探查**：`risks` 中 `zero_unit_price`（`unit_cost` 为 0）、`stamping_calc_failed`；`mom_anomalies.items`（相对上月单价绝对值 ≥ 10%）
- **作业台核对**：`summary.pending_audit_total` / `incomplete_total` / `pending_confirm_total`，以及 `boards` 各切片件数；`risks` 中 `pending_audit` / `calc_incomplete` / `pending_confirm`
- **模具费**：`pending_audit_count`、`zero_fee_count`、`final_die_fee_sum`
- **检具费**：`effective_count`、`invalid_count`、`zero_fee_count`
- **采购对象**：`pending_confirm_count`、`pending_audit_count`、`anomaly_count`
- **年度零件价 / 一口价探查**：`annual_price_anomalies.items`（`skipped_conversion`：核价单价≈采购单价、未除转换系数；`fine_unit_unconverted`：桶/瓶对毫米但系数为 1）；`standard_part_anomalies.items`（`standard_part_high_price`：标准件/胶块计件单价过大）

## 何时写（比较 / 趋势类例外）

用户问**比较、对比、变化、趋势、全年**时，须按 `comparison_advice_rules.md` 在「建议」**之前**写「风险提示」；无异常时一句带过即可。

其余场景仍按上文「何时写」：仅在有异常线索或用户关心可靠性时提及，禁止空章灌水。

## 怎么写

- 融入相关段落，用 1～3 句说明事实与对结论的影响即可。
- **比较 / 趋势类**可用二级标题「风险提示」（见 `comparison_advice_rules.md`）；其他场景禁止为凑格式单独开「异常与风险」空章。
- 有样本则引用 JSON 已给零件号（勿编造）。

## 成品 vs 冲压域（part_existence）

- `part_existence.primary_source = l0`：成品供货总成，只在成品核价一览建账。
- `stamping_cost.applicable = false` 等：**数据源不适用**，不是缺数据、不是风险。
- **禁止**把「成品在 L0 已找到，但冲压库未命中」写成异常。
- 只有 `applicable = true` 且 `found = false` 时，才可提示该库未命中。

## 加减价 vs 基准价（口语对照）

采购同事口头常说 **「加减价」**，不一定说「政策」；与 **「中标价」= 基准价** 一样，须先对齐口径再写异常：

| 用户口语 | 实际数据 | 异常线索 JSON | 核对入口（正文可写） |
|---------|---------|--------------|-------------------|
| 加减价 / 厚度加减 / 宽度加价 | 加减价政策列表（`steel_price_policy`） | `policy_anomalies.items` | 加减价政策列表 |
| 中标价 / 基准价 | 基准价格列表（`steel_base_price`） | `base_price_anomalies.items` | 基准价格列表 |

- 用户问加减价有无异常、传错、跳变时：按 `comparison_advice_rules.md`「加减价探查类」出表；**正文沿用用户口语「加减价」**，不要刻意改成「加减价政策」除非需要指明菜单页。
- 禁止把加减价异常写成基准价异常，或混用「中标厚度一览」。

## 禁止

- 禁止把 `partial` 说成「已全部完成」。
- 禁止在 JSON 无证据时编造「同步失败」「钢厂违约」等故事。
- 禁止用「加强管理」代替可执行动作。
