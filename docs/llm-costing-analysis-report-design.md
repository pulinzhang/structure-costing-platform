# 核价结果智能分析 — 产品架构设计

> 状态：**架构定稿**（时间范围 + Repository 直读；Query / Repository / Analysis / Snapshot 边界锁定）  
> 业务主体：冲焊装配供应商（可多租户售卖）· 主用户：**采购部**  
> 关联：`docs/costing-engine-design.md`、`docs/l0-assembly-costing-design.md`、`docs/architecture.md`  
> 参考：仅借鉴「预聚合事实 + 强约束 Prompt」；不复用 Chat/SSE

---

## 0. 一句话原则

> **数字由系统计算，事实由系统提供，确定性结论由 Analysis 算出，业务解释与判断由 LLM 完成。**  
> 产品目标不是「正确生成 Markdown 报告」，而是：**采购用约 30 秒发现问题 → 看到证据 → 点下一步动作。**

核价引擎是唯一算价真相源。LLM **不得**重算单价、改公式、自行汇总环比/占比/贡献度。

本产品本质不是固定报表生成器，而是：

> **基于核价结果库的分析查询系统 + LLM 自然语言解释层。**  
> **时间范围**与**可比口径（comparison_basis）**同为一等能力。

### 0.1 取数与计算总原则

> **LLM 分析模块允许直接访问业务结果表（经本切片只读 Repository），但禁止绕过数据权限与业务口径。**  
> **Repository 负责把时间范围内的事实查出来（可含 SQL 层查询聚合）。**  
> **Analysis 负责把事实变成趋势、比较、动因和异常（业务分析逻辑）。**  
> **Snapshot 只保存「本次分析」的确定性结果。**  
> **LLM 不计算数字，而是理解这些结果、解释原因、形成业务判断。**

```text
                    用户问题
                       │
                       ▼
                 AnalysisQuery
              ┌────────┴────────┐
              │                 │
           时间范围 + 过滤      分析意图
           (+ 可比口径)         (trend/driver/…)
              │                 │
              └────────┬────────┘
                       ▼
                  Repository
                       │
              原始事实 / SQL 查询聚合
                       ▼
                   Analysis
       ┌────────┬──────┼──────┬────────┐
       ▼        ▼      ▼      ▼        ▼
     Trend    Driver Compare Risk   Drilldown
       │        │      │      │        │
       └────────┴──────┼──────┴────────┘
                       ▼
                AnalysisSnapshot
                       │
              ┌────────┴────────┐
              ▼                 ▼
             UI                 LLM
        数字/图表/证据       解释/判断（Markdown）
```

| 约定 | 说明 |
|------|------|
| 取数 | **`llm` Repository 直读**结果表；可含参数化 SQL / ORM **查询聚合** |
| 时间范围 | **一次**按起止条件查出，再交给 Analysis；禁止按月循环调上游 Service 拼装 |
| 数字对比 | **Analysis 先算** trend / comparison / driver，再交给 LLM 解释 |
| 结论边界 | **确定性结论**由 Analysis；**业务解释与判断**由 LLM |
| 产品入口 | **分析类型由系统从问题推出**；用户不必选择报表/mode 菜单 |

**禁止：** 改写业务结果表、触发算价 Orchestrator、绕过租户/基地数据权限、让 LLM 自己算环比与占比、把 Repository 做成第二个 Analysis Service、把明细堆给 LLM 自行比大小。

---

## 1. 设计目标与反模式

本设计要避免下列反模式：

| 反模式 | 问题 |
|--------|------|
| 按月循环调 Service 再拼装喂模型 | 时间趋势要调 N 次，绕远、难做区间查询 |
| 重型自然语言意图引擎 | 做成小型 NL Query Engine；采购问法高度重复 |
| `report_type` / 用户选 mode 菜单 | 助手变成报表/菜单路由器 |
| 碎装数据包 + 万能结果抽屉 | 维护成本高，一次分析却塞满无关块 |
| 跨维查明细交 LLM 自己比 | 数字对比不稳，随基地×月膨胀 |
| 只谈时间、不谈口径 | 制造业「涨了 8%」可能是 BOM/工艺变了，不是价格趋势 |
| 聊天历史只存浏览器 | 企业需要可重开的分析记录 |
| 输出停在 Markdown、缺 Snapshot 证据 | 采购看不到数字与口径，无法核对 LLM 判断 |

**工程底线：** 不改核价公式、金额单位「元」、异常必显、异步任务、浮动壳、权限与审计。

---

## 2. 产品形态：问题驱动，不是菜单驱动

对外不讲「请选择 Overview / Analyze / Drilldown」。用户只提问（或点胶囊人话），系统内部组合分析能力：

```text
用户问题
   ↓
AnalysisQuery
   ↓
系统决定需要哪些分析能力（可组合）
   ├── Summary（盘子）
   ├── Trend（趋势）
   ├── Drivers（动因）
   ├── Comparison（对比）
   ├── Risk（风险/缺价）
   └── Drilldown（单号）
   ↓
Snapshot（只含本次用到的结果）
   ↓
UI 数字 + LLM 解释（Markdown）
```

| 用户问法（示例） | 系统内部组合（示例） |
|------------------|----------------------|
| 这个月采购成本怎么样？ | Summary + Risk |
| 今年青岛 T28 成本怎么变化？ | Summary + Trend |
| 哪些零件涨得最快？ | Drivers（+ Trend） |
| 青岛和芜湖谁涨得更多？ | Comparison |
| 501006875AA 最近半年为什么涨？ | Drilldown + Trend + Drivers |

胶囊只是「填入一句人话」；**不是**让用户选择报表类型。API 可保留内部 `analyses[]` 枚举供实现，**禁止**把三 mode 做成产品主菜单。

**时间范围**是分析主轴之一（单月 = start=end）。另见 §4.3 **可比口径**。

### 2.1 交互

- 壳层浮动助理；不挂侧栏、不占主内容区；遮罩不压暗原表  
- 胶囊一键发常见问法；自由输入可选，轻量解析即可  
- 无 SSE；AsyncTask + 轮询；整包返回  

---

## 3. 四层架构

```text
① Query 解析 → AnalysisQuery（filters + time_range + comparison_basis + analyses）
② Repository（查）→ 事实行 / SQL 查询聚合行
③ Analysis（算）→ trend / driver / compare / risk / drilldown 确定性结果
④ Snapshot（本次结果）→ UI + LLM 解释
```

| 层 | 职责 | 不做 |
|----|------|------|
| **Query** | 结构化「查什么范围、以什么口径、做什么分析」 | 不算金额；不调模型做完备意图（P0） |
| **Repository** | **查**出时间范围内的事实；可做 **DB 查询聚合** | **不做**业务分析逻辑（见 §5） |
| **Analysis** | **算**趋势/对比/动因/异常/排序/贡献 | 不调 LLM；不改单价公式；不直接堆原始明细给 Prompt |
| **Snapshot + LLM** | 保存本次确定性结果；LLM **解释与业务判断**（Markdown） | LLM 不发明数字；聊天区不生成跳转按钮 |

> **Repository 负责查，Analysis 负责算，Snapshot 保存本次结果，LLM 负责解释与判断。**

依赖：`llm` 独立下游；可 import 上游结果表 Model；不经上游 Service→VO 取分析主数据；不被 `costing` 反向依赖。

---

## 4. AnalysisQuery：拆成「范围」+「意图」，避免过早 OLAP 化

**不要**把 Query 做成不断膨胀的「用户能问什么」字段清单（supplier / thickness / workshop… 无限加字段）。

拆成两层：

### 4.1 Query Scope（查什么范围）

```json
{
  "time_range": {
    "start": "2026-01",
    "end": "2026-08"
  },
  "filters": {
    "location": "青岛",
    "vehicle_model": "T28",
    "bom_version": "V1"
  },
  "subject": "cost_total",
  "comparison_basis": {
    "same_part": true,
    "same_bom_version": true,
    "same_material": false,
    "same_process": false,
    "label": "same_bom_version"
  },
  "user_question": "今年青岛 T28 采购成本怎么变化？"
}
```

| 字段 | 说明 |
|------|------|
| `time_range` | **一等公民**；`start`/`end` 用 `YYYY-MM`；单月则相同 |
| `filters` | **开放字典式过滤**，只放本次已知维度；新增维度加 filter key，不改 Query 根结构 |
| `subject` | 分析对象粒度：`cost_total` / `steel_price` / `part` / `l0` / …（短枚举，按需增） |
| `comparison_basis` | **可比口径**（§4.3）；趋势/对比必须声明 |

`filters` **不要**在 Schema 根上提前铺平 `supplier`、`thickness`、`process`…；需要时再进 `filters`，避免长成小型 OLAP 语言。

### 4.2 Analysis Intent（做什么分析）

```json
{
  "analyses": ["summary", "trend"]
}
```

或由解析器从问题推出（可组合，不是单选菜单）：

| `analyses` 值 | 含义 |
|---------------|------|
| `summary` | 盘子/结构/缺价计数 |
| `trend` | 时间序列趋势 |
| `drivers` | 涨跌动因 TopN |
| `comparison` | 跨基地/跨区间对比 |
| `risk` | 缺价 / partial / gate |
| `drilldown` | 单号分解（通常配合 `filters.part_number`） |

示例：「今年青岛 T28 哪些零件成本涨得最快？」

```json
{
  "time_range": { "start": "2026-01", "end": "2026-08" },
  "filters": {
    "location": "青岛",
    "vehicle_model": "T28"
  },
  "subject": "part",
  "comparison_basis": {
    "same_part": true,
    "same_bom_version": true,
    "same_material": false,
    "same_process": false,
    "label": "same_part_and_bom"
  },
  "analyses": ["drivers", "trend"],
  "user_question": "今年青岛 T28 哪些零件成本涨得最快？"
}
```

「501006875AA 最近半年为什么涨这么多？」→ `analyses: ["drilldown","trend","drivers"]`，`filters.part_number` 有值。

### 4.3 可比口径 `comparison_basis`（制造业必补）

**时间相同 ≠ 可直接比。** BOM 变了、材料规格变了、工艺变了、核价公式版本变了、产品状态变了，则「3 月比 1 月涨 8%」可能是对象变了，不是价格趋势。

```json
{
  "comparison_basis": {
    "same_part": true,
    "same_bom_version": true,
    "same_material": true,
    "same_process": true,
    "same_formula_version": false,
    "label": "same_part_bom_material_process",
    "notes": "仅同零件号+同 BOM 版本纳入趋势；材料/工艺未对齐时不得宣称「纯价格上涨」"
  }
}
```

| 要求 | 说明 |
|------|------|
| 趋势/对比必带 | Snapshot.meta 必须标明本次是 **同口径可比** 还是 **全量结果趋势（口径可能漂移）** |
| Analysis 遵守 | `trend`/`drivers`/`comparison` 按 basis 过滤或分组；无法对齐时输出 `comparability: "loose"` 与原因 |
| LLM 遵守 | 口径为 loose 时，解释中必须写明「可能含 BOM/工艺变更，不单是价格变动」 |
| UI | 显著展示口径标签，避免采购把「对象变化」当成「钢价上涨」 |

P0 至少实现：`same_part` + `same_bom_version` 开关与文案；材料/工艺/公式版本可先占位，在 meta 中声明「未校验」。

### 4.4 Query Parser 轻量实现（`query_parser.py`）

> 目标：自然语言灵活，但 **IntentParser 不做成重型 NLU / 自研规则森林**。  
> 解析器只负责抽出「范围与对象线索」，**不做金额计算、不选报表类型、不调业务 Service 取数**。

#### 4.4.1 职责分工（最优雅切分）

| 谁 | 干什么 |
|----|--------|
| **LLM** | 口语 → 干净 JSON：`time_range` + `filters`（+ `compare_locations`） |
| **Python** | 词典对齐、定 `analyses[]` / `subject`、环比/TopN、组 Snapshot |
| **SQL/Repo** | `WHERE` / `GROUP BY` / `SUM` 精确取数 |

```text
POST body：仅 user_question
        │
        ▼
┌───────────────────────────────────────┐
│ A. ConditionExtractor（LLM，t=0）       │
│    + 当前年月锚点；JSON Mode            │
│    只吐 time_range / filters            │
└───────────────────┬───────────────────┘
                    ▼
┌───────────────────────────────────────┐
│ B. EntityAligner（Python）              │
│    「青岛厂」→ location:"青岛"          │
└───────────────────┬───────────────────┘
                    ▼
┌───────────────────────────────────────┐
│ C. QueryParser 规则（Python）           │
│    定 analyses / subject / basis        │
│    → AnalysisQuery → Runner → SQL       │
└───────────────────────────────────────┘
```

前端**不要求**用户填写基地/年月/车型/BOM scope；胶囊与输入框都是一句人话。

#### 4.4.2 抽取契约（LLM Structured Output 仅限此 Schema）

```json
{
  "time_range": { "start": "2026-01", "end": "2026-08" },
  "filters": {
    "location": "青岛厂",
    "vehicle_model": "T28"
  },
  "compare_locations": []
}
```

| 规则 | 说明 |
|------|------|
| LLM 只做抽取 | 不得输出金额、结论、`analyses` |
| `response_format=json_object` + `temperature=0` | API 级约束 + 确定性 |
| 未提时间 | `time_range` 默认 = 当前年月（start=end） |
| 入口无 scope | 条件一律从 `user_question` 抽出 |

相对时间说法归一（规则层可再校正）：

| 用户说法 | `time_range` |
|----------|--------------|
| 这个月 | start=end=当前系统月 |
| 近三个月 | end=当前月，start=end-2 |
| 今年以来 / 1月到8月 | start=当年-01 或明示，end=明示或当前月 |
| 过去半年 | end=当前月，start=end-5 |

#### 4.4.3 Schema 词典对齐（强制）

抽取得到的是**口语实体**，必须经本系统词典 / scope-options 对齐后才能进 `filters`：

| 步骤 | 做法 |
|------|------|
| 加载词典 | 基地、车型、BOM 版本等来自 `scope_options_repository` DISTINCT + 受控别名表（如「青岛厂」「青岛基地」→ `青岛`） |
| 对齐 | 精确匹配 → 别名表 → （可选）规范化去后缀「厂/基地」；**禁止**模糊到错误主数据 |
| 失败策略 | 对齐失败：该 filter **不写入** Query，并在 Snapshot.meta 记 `unresolved_mentions` |
| 零件号 | 正则抽出后与结果表存在性可选校验；不存在则 drilldown 分析标注无数据，不编造 |

```text
「青岛厂」 --词典对齐--> filters.location = "青岛"   ✅
「胶东那边」 --无法对齐--> 丢弃 + unresolved_mentions   ✅（不臆造）
```

#### 4.4.4 `analyses` 怎么定（纯 Python 规则）

| 线索 | 追加 |
|------|------|
| 默认 | `summary` |
| 跨月 / 「趋势」「涨跌」 | `trend` |
| 零件号 / 「零件号」 | `drilldown` |
| 「对比」「谁更」/ 多基地 | `comparison` |
| 「缺价」「partial」 | `risk` |

**不做：** 让 LLM 选 analyses；重型意图分类；要求用户先选 Overview/Analyze/Drilldown。

解析只产出完整 `AnalysisQuery`；**不**在解析器里循环调 Service / 查金额。

---



## 5. Repository ↔ Analysis 边界（必须定死）

### 5.1 总规则

> **Repository 可以做数据库层面的「查询聚合」，但不能承载业务分析逻辑。**  
> **Analysis 不做「再查一遍库换写法」，只消费 Repository 返回的事实/查询聚合结果。**

```text
Repository                          Analysis
──────────                          ────────
WHERE / JOIN                        MoM / YoY
GROUP BY month|part|location        Change Rate / 累计涨幅
SUM / AVG / MIN / MAX / COUNT       Contribution（贡献度）
DISTINCT（scope 下拉）               Ranking / TopN（业务排序规则）
BETWEEN start AND end               Anomaly（业务异常判定）
权限过滤（tenant/location）          Trend 形态摘要、可比口径对齐后的对比
```

| 允许放在 Repository | 必须放在 Analysis |
|---------------------|-------------------|
| `SUM(amount) GROUP BY year, month` | 环比、同比、累计涨幅 |
| `AVG(price) GROUP BY spec, month` | 贡献度、头部集中度 |
| 按 `part_number` 过滤的明细行 | TopN 业务排序（含并列规则） |
| 区间内 raw rows（有行数上限） | 异常月/异常件判定 |
| | 跨基地「谁涨得更多」的结论字段 |
| | 按 `comparison_basis` 做可比对齐后的差分 |

**禁止：** Repository 方法名叫 `analyze_*` / `compute_mom_*`；在 Repository 里写「值得议价」类业务判断；Analysis 里再写一套绕过 Repository 的 SQL。

### 5.2 正确 vs 错误（时间范围）

```text
正确：
  Repository.query_monthly_totals(filters, start, end)
    → [{month, sum_amount}, ...]   // SQL GROUP BY 即可
  Analysis.trend(rows, comparison_basis)
    → {points, mom_rates, cumulative_change, anomalies, comparability}

错误：
  for m in 1..8: 按月分页取数 → 把多月明细堆给 LLM 自己比

错误：
  Repository.get_trend_with_mom_and_top_drivers(...)  // 业务分析泄漏进 Repository
```

### 5.3 Repository 约定

```python
# 示意：只做查询与查询聚合
def query_l0_monthly_totals(
    db: Session,
    *,
    filters: dict[str, str],
    start: str,  # YYYY-MM
    end: str,
    tenant_id: ...,
) -> list[MonthlyTotalRow]:
    """WHERE + GROUP BY month + SUM；不含环比/贡献度。"""
    ...
```

| 规则 | 说明 |
|------|------|
| 可直读 | 结果表 Model；参数化 ORM / SQL |
| 返回 | 本切片行 / 查询聚合 TypedDict；**不是**上游列表 VO，**不**包 ApiResponse |
| 权限 | WHERE 必带租户/基地等与现网一致的范围 |
| 禁止 | 写业务表；调算价 Orchestrator；按月循环调上游 Service；实现 MoM/贡献度/议价判断 |

---

## 6. Analysis：确定性计算（可组合）

按 Query.`analyses` **按需执行**模块，结果写入 Snapshot.`result`（见 §7），不要每次跑全套。

| 模块 | 输入 | 输出（确定性） |
|------|------|----------------|
| `summary` | 查询聚合行 / 计数 | 盘子、结构占比（占比若由总额相除，属确定性算，可在 Analysis） |
| `trend` | 月序列 + comparison_basis | 点列、高低点、累计变化、逐月环比、异常月、`comparability` |
| `drivers` | 对象多期值 + basis | start/end/change/change_rate、TopN、贡献度 |
| `comparison` | 多序列 | 各涨幅、差值、winner 字段 |
| `risk` | partial/缺价/gate 事实 | risks 列表 |
| `drilldown` | 单号事实 | 分解行 + 区间差分 |

**确定性结论**示例（Analysis 写进 Snapshot，LLM 不得改数字）：

- 「青岛 1–8 月累计 +8.7%，芜湖 +3.2%」  
- 「Top3 零件贡献了区间涨幅的 62%」  
- 「本次趋势口径：同零件号+同 BOM（loose/tight）」  

**业务解释与判断**示例（LLM，须基于 Snapshot 证据）：

- 「本次上涨主要受钢材价格变化影响」（需 Snapshot 中有钢材动因证据）  
- 「该零件值得优先与供应商重新议价」（建议口吻；不替代人工拍板）  

### 6.1 场景

**趋势：** Repository 一次查出 8 个月 `GROUP BY month` 合计 → Analysis.trend → LLM 叙述阶段变化。  
**动因：** Repository 区间零件行或按件汇总 → Analysis.drivers Top20 → LLM 归纳集中在哪类件。  
**对比：** Repository `location IN (…) AND month BETWEEN` → Analysis.comparison 算出两侧涨幅 → LLM 解释差距。

---

## 7. AnalysisSnapshot：本次结果，不是万能容器

> **Snapshot 是「本次分析结果」，不是「所有可能数据的抽屉」。**

用户只问钢材趋势时，**不要**塞 `parts` / `gate` / `drivers` / `comparison` 空壳。

### 7.1 形状

```json
{
  "query": { },
  "meta": {
    "has_data": true,
    "comparability": "tight",
    "comparison_basis_label": "same_part_and_bom",
    "currency_note": "金额单位：元；禁止改写为万元",
    "generated_at": "…",
    "data_message": "…"
  },
  "summary": { },
  "result": {
    "kind": "trend",
    "trend": { }
  },
  "evidence": {
    "series": [ ],
    "samples": [ ]
  }
}
```

| 块 | 含义 |
|----|------|
| `query` | 回显本次 AnalysisQuery（含 time_range、filters、basis、analyses） |
| `meta` | 有无数据、**可比口径标签**、币种、生成时间 |
| `summary` | 可选；仅当 `analyses` 含 summary 或需要一句话 KPI 时出现 |
| `result` | **按分析类型分化**：`kind` = trend \| drivers \| comparison \| risk \| drilldown \| composite |
| `evidence` | 支撑 result 的少量序列/样本（已裁剪），供 UI 表与 LLM 引用 |

`result.kind = "composite"` 时：

```json
"result": {
  "kind": "composite",
  "parts": {
    "drilldown": { },
    "trend": { },
    "drivers": { }
  }
}
```

只放入本次 `analyses` 请求过的部分。

### 7.2 喂给 LLM

```text
System：采购助手；只引用 Snapshot；禁止重算；口径 loose 必须说明；异常必写
User ：user_question + Snapshot JSON（已按本次 analyses 裁剪）+ 字段词典
```

UI：**数字/表/图以 Snapshot 为准**；Markdown 是解释与判断。

---

## 8. 列表页落点（`menu_catalog.py`，仅服务端路由/测试）

助理**问什么答什么**：聊天区只展示 Markdown 正文，**不生成跳转按钮或深链 Action**。

`menu_catalog.py` 保留 `subject → hash_page` 映射，用于：

- Query Parser / 菜单问句回归测试（`tests/llm/test_menu_questions.py`）
- 侧栏覆盖审计（`MENU_COVERAGE`）

| `subject` | 用户说法示例 | 落点 |
|-----------|--------------|------|
| `l0` / `cost_total` | 成品成本、采购成本、供货总成 | `#/l0-assembly-cost` |
| `stamping_part` | 冲压件、冲压零件成本 | `#/stamping-part-cost` |
| `steel_price` | 钢材、钢价、联动价 | `#/steel-price-list` |
| `steel_price_policy` | 加减价、厚度加减价 | `#/steel-price-policy-download` |
| `steel_base_price` | 基准价、中标价 | `#/base-price-download` |

帮助类问题走 `usage_help` 模式，语料来自 `static/helper/*.html`，不经 `menu_catalog` 深链。

---


## 9. 持久化与 API

| 存哪 | 存什么 |
|------|--------|
| 服务端分析记录 | Query、Snapshot、explanation（Markdown）、审计字段 |
| localStorage | 仅 UI 与 `analysis_id` 引用 |

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/llm/reports` | body：**仅** `user_question`（+ 可选 `audience` / `force_refresh` / `idempotency_key`） |
| `GET` | `/api/llm/tasks/{task_id}` | 轮询 |
| `GET` | `/api/llm/reports/{id}` | Markdown 正文 + 元数据 |
| `GET` | `/api/llm/reports` | 历史 |

**对外请求不传 scope / analyses[]；analyses 由条件抽取后在服务端组合。** 不以 `mode=overview|analyze|drilldown` 作为产品概念。

```json
{
  "user_question": "2026年1月到8月，青岛采购成本怎么变化？",
  "force_refresh": false,
  "idempotency_key": null
}
```

---

## 10. 目录建议

```text
app/services/llm/
    query/
    query_parser.py       # NL → LLM 条件抽取 → 词典对齐 → AnalysisQuery
    condition_extractor.py
    entity_aligner.py     # Schema 词典 / scope-options 对齐（「青岛厂」→「青岛」）
    time_range.py
    comparison_basis.py   # 口径默认值与校验
  analysis/
    summary.py
    cost_trend.py         # MoM、累计涨幅、异常月（业务分析）
    cost_driver.py
    comparison.py
    anomaly.py
    drilldown.py
    runner.py             # 按 analyses[] 组合执行
  context/
    snapshot_builder.py   # 只组装「本次」Snapshot
    field_labels.py
  generator.py
  report_service.py
  usage/                  # 帮助语料检索（usage_help 模式）

app/repositories/llm/
  cost_analysis_repository.py     # WHERE/GROUP BY/SUM 等查询聚合
  steel_price_analysis_repository.py
  stamping_cost_analysis_repository.py
  scope_options_repository.py
  report_repository.py

app/schemas/llm/          # AnalysisQuery / Snapshot
app/routers/llm/
static/js/llm-assistant/
```

| 模块职责 | 落点 |
|----------|------|
| 查事实 / SQL 查询聚合 | `repositories/llm/*` |
| 业务分析（trend/driver/…） | `services/llm/analysis/*` |
| 组装本次 Snapshot | `context/snapshot_builder.py` |
| 问题 → AnalysisQuery | `query/query_parser.py`（+ 词典对齐） |
| Snapshot 形状 | `query` / `meta` / `summary?` / `result` / `evidence`；按需填充 |
| 产品入口 | `analyses[]` 由解析/胶囊组合；非用户报表菜单 |

---

## 11. 约束清单

| # | 约束 |
|---|------|
| R1 | 纯 REST；整包返回；无 SSE/WebSocket |
| R2 | 异步任务 + 轮询为主路径 |
| R3 | 不改核价公式；LLM 不重算、不改单位为万元 |
| R4 | **业务分析逻辑（MoM/贡献度/TopN/异常）只在 Analysis**；Repository 仅查询与查询聚合 |
| R5 | **时间范围一等公民**；一次按起止条件查询；禁止按月循环 Service |
| R6 | 允许 `llm` 只读 Repository 直读结果表；禁止绕过数据权限与业务口径；分析主数据不经上游 Service→VO 拼装 || R7 | Query = Scope（filters+time+basis）+ Intent（analyses[]）；避免根级字段无限膨胀 |
| R8 | **comparison_basis 必出现在趋势/对比类分析**；Snapshot.meta 标明 tight/loose |
| R9 | Snapshot 只含本次结果；禁止万能大杂烩空块 |
| R10 | 分析类型由系统组合；禁止把 Overview/Analyze/Drilldown 当用户主菜单 |
| R11 | 确定性结论归 Analysis；业务解释与判断归 LLM |
| R12 | **问什么答什么**：聊天区仅 Markdown；不返回 Action 按钮；帮助走 `usage_help` + helper 语料 |
| R13 | Query Parser：规则优先；可选 Lightweight LLM **仅 Structured Output 抽取**；抽出实体须经 Schema 词典对齐；禁止 Parser 内算金额或臆造主数据 |
| R14 | 服务端落分析记录；localStorage 仅 UI |
| R15 | 壳层浮动助理；异常/缺价/口径漂移必显 |
| R16 | 轻量 Query 解析；不做完备 NL Query Engine（P0） |

**非目标：** Tool Calling 开放域、流式打字机、侧栏分析菜单、自动议价发函、向量 RAG（首期）、LLM 算环比、Repository 内实现业务分析、按月调 Service 冒充时间范围。

---

## 12. 分期

| 阶段 | 交付 |
|------|------|
| **P0** | Query Parser + Repository 区间查询 + Analysis + 瘦 Snapshot + 落库 + 壳层；`usage_help` 帮助模式；comparison_basis 最小集 |
| **P1** | comparison；drilldown 组合；口径校验增强；历史列表 |
| **P2** | 材料/工艺/公式版本对齐；导出；审计增强 |

---

## 13. 验收口诀

> **30 秒内能指出一个问题，并立刻点到证据和下一步；若口径不可比，必须看得见。**

| 场景 | 通过 | 失败 |
|------|------|------|
| 趋势 | 一次区间查询 + Analysis 环比与库一致 + **展示口径标签** | 循环 Service / 模型自己数月 / 隐瞒 BOM 变更 |
| 贵在哪 | drivers 含 rate，数字出 Analysis | 模型估算涨幅 |
| 跨基地 | comparison 出 Analysis | 明细堆 Prompt 让模型比 |
| 单号组合 | drilldown+trend 同次 Snapshot，无多余空块 | 塞满无关 gate/parts |
| 帮助 | usage_help 命中 helper 语料，步骤可操作 | 编造菜单路径或操作 |
| Parser | 「青岛厂」对齐为 `青岛`；未知实体进 unresolved | Parser 臆造基地或直接算涨幅 |
| 审计 | 按 analysis_id 重开 | 清缓存无法找回 |

---

## 14. 决策摘要（评审用）

| 议题 | 决策 |
|------|------|
| 产品本质 | 核价库分析查询系统 + LLM 解释/判断层 |
| Repository vs Analysis | SQL 查询聚合在 Repo；MoM/贡献度/TopN/异常在 Analysis |
| Query | Scope（filters+time+basis）+ Intent（analyses[]）；不做过早 OLAP 字段森林 |
| 可比口径 | `comparison_basis` 一等公民；趋势必标 tight/loose |
| Snapshot | query/meta/summary/result/evidence；按需填充 |
| 三 mode | 非用户菜单；系统组合 analyses |
| LLM | 不算数；可做业务解释与判断（有证据） |
| 帮助 | `usage_help` + `static/helper` 语料；不查核价库 |
| Query Parser | 规则优先 + 可选 Structured Output 抽取 + 词典对齐；非重型 NLU |
| 取数 | **`llm` Repository 直读**结果表；按条件/时间范围查询；遵守权限与口径 |
---

## 15. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-23 | 同步 §0.1 / §2 / §3 等 Actions 过时表述；§0.1 流程图即分层主图 |
| 2026-08-23 | 移除 ActionBuilder / 聊天区深链；Snapshot 无 actions；新增 usage_help 与成品核价卡住 FAQ |
| 2026-08-22 | 初稿：分析查询系统 + LLM 解释层；四层边界；时间范围与可比口径；Query Parser |

---

*实现以 §0 / §3 / §4 / §5 / §7 / §11 为准。*
