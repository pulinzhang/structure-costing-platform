# LLM 确定性分析（`analysis/`）

按问句 `AnalysisQuery` 查库并算出 summary / trend / risk / drilldown。  
对外入口：`from app.services.llm.analysis.runner import AnalysisRunner, AnalysisRunResult`。

切片导读（整条提问链路）：`docs/llm/llm-slice-design.md`。

## 架构

```text
AnalysisRunner          # 薄分发，只看 query.subject
  OpsAnalysis           # 作业台 / 模具费 / 检具费 / 采购对象
  StampingAnalysis      # 工艺 / 冲次 / 加工费 / 零件价
  SteelAnalysis         # 联动价 / 政策 / 基价 / 中标厚度 / 废料
  WeldingAnalysis       # 焊接单价 / 拆解 / 成品焊接费
  BomAnalysis           # 年价 / 包装运输 / 材料清单
  AssemblyAnalysis      # 成品核价 / 零件存在性 / 单件问价
```

公式与口径在 `shared/`，不进主题 runner。

## 目录

| 包 | 职责 |
|----|------|
| `runner.py` | 薄分发；仍 re-export `AnalysisRunResult` |
| `shared/` | 结果容器、公式、口径、趋势/驱动/异常/下钻 |
| `ops/` | 作业台与主数据类档案 |
| `stamping/` | 冲压工艺与零件价 |
| `steel/` | 钢价与一事一议价格 |
| `welding/` | 焊接三张表 |
| `bom/` | BOM 年价 / 包装运输 / 材料 |
| `assembly/` | 成品核价卡与单件问价 |
