请根据下列 JSON，**直接回答**用户问题。

## 用户问题

{user_question}

## 数据（唯一来源）

```json
{context_json}
```

## 铁律

1. **问什么答什么**：只写与问题直接相关的内容；禁止套「完整分析报告」模板。
2. **比较 / 对比 / 变化 / 趋势 / 全年**：按 `_shared/comparison_advice_rules.md` 与 `_shared/scope_rules.md` — 先核对 `scope.time_range` 与 `scope.month_count`；仅 `is_full_calendar_year=true` 时可写「全年」；先「风险提示」，再「建议」（各简短）；单月概况且无对比意图时不要写这两段。
2b. **总成核价异常 / 单价为 0 / 相对上月偏差 / 构成独大 / 标准件单价过大**：按 `_shared/comparison_advice_rules.md`「总成核价探查类」列表；只引用 `zero_unit_price`、`mom_anomalies`、`composition_anomalies`、`standard_part_anomalies`，禁止自行重算。
2c. **冲压核价异常**：按「冲压零件核价探查类」；只引用当月 JSON。
2d. **焊接成本计算 / 焊接费异常**：按「焊接成本计算探查类」；环比是年，不是月。
2e. **核价进度 / 待审核 / 还没确认外发**：按「作业台核对类」；模具费、检具费、采购对象用各自 summary，禁止自行加总。
2f. **年度零件价 / 一口价 / 标准件价格异常**：按「年度零件价 / 一口价探查类」；只引用 `annual_price_anomalies` 与 `standard_part_anomalies`，禁止自行用采购单价÷转换系数另算一遍当结论数字（表里的应有核价单价可引用）。
3. 数字只能来自上述 JSON；禁止编造。
3. 金额单位是 **元**，禁止写成万元，禁止 ÷10000。
4. **全文中文白话**；禁止英文字段名、代码术语；遵守 `_shared/chinese_style_rules.md`。
5. **禁止**在正文写「报告类型」「受众」「数据生成日期」等元信息；标题贴合用户问题即可，不要写「概览分析」类标签。
6. 无数据时简短说明原因，不要展开无关板块。
7. 不要输出 UTC 技术时间戳；不要写 dashboard / 仪表盘内容（除非用户原话如此）。
8. `part_existence` 中成品供货总成、不适用数据源，不得写成风险。
