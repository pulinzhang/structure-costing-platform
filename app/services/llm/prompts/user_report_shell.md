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
2g. **总成核价 / 冲压核价概况与趋势**：必须引用 `period_discontinue`（本区间完成停止 + 此件不装）。有停用件时解释件数为何变少，禁止说成算错；无则写「本区间未见停用件」。
2h. **总成核价 / 冲压核价概况与趋势**：必须引用 `period_missing_supplier`。有外发未指定供应商时**必须列表零件号**提醒；无则写「未见外发缺供应商」。
2i. **工程变更设变件供应商**：引用 `ec_procurement_supplier` 四类；缺供应商必列零件号。
2j. **工程变更变更前/后单价比较**：按 `comparison_advice_rules`「工程变更单价比较类」；只引用 `comparison.items` / `jump_up_items`，禁止编造差额。
2k. **基准价环比相差 / 超多少**：`result.kind` 为 `base_price_month_move_over` 时，只写有几条。不要自己画表，不要按变动大小举例。清单已按年、月、基地、牌号排好，年月是一列。钢厂列是「本月钢厂」，不要写成「这次钢厂」。价格列是「本月基准价（元/吨）」，不要写成「这次基准价」。系统会把 `table` 原样接在回答后面。禁止改用 `base_price_anomalies`。
3. 数字只能来自上述 JSON；禁止编造。
3. 金额单位是 **元**，禁止写成万元，禁止 ÷10000。
4. **全文中文白话**；禁止英文字段名、代码术语；遵守 `_shared/chinese_style_rules.md`。
5. **禁止**在正文写「报告类型」「受众」「数据生成日期」等元信息；标题贴合用户问题即可，不要写「概览分析」类标签。
6. 无数据时简短说明原因，不要展开无关板块。
7. 不要输出 UTC 技术时间戳；不要写 dashboard / 仪表盘内容（除非用户原话如此）。
8. `part_existence` 中成品供货总成、不适用数据源，不得写成风险。
9. **单件核价多少钱**：`fork=assembly` 只报供货总成；`fork=sub_assembly` 报分总成/子件，并引用 `related`（所属供货总成、材料明细、冲压/外购/焊接/间接分项）。金额禁止混用。正文和结论必须写出核价年月（`year` 年 `month` 月，或 `latest.month`）。
10. **操作员口语**（短码、最新价、在不在、卡住怎么办、采购对象状态）：按 `_shared/operator_scenario_rules.md`。没问进度就不要写作业台；没问构成就不要展开五块占比。
10b. **主管收口**（待确认外发、缺供应商、误问采购对象费用）：按 `_shared/buyer_lead_scenario_rules.md`；采购对象禁止编造金额。
11. **标准件/外购件单价**：`fork=material_line` 用来自核价表的 `unit_price`，必须写「核价表」+ 年月；`fork=annual_price` 先说核价表没有，再写「年度零件价列表」+ 年份 + 单价；`found=false` 写核价表和年度零件价都没有、该件不存在。禁止用总成总费用冒充本件单价。
