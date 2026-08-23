# 核价结果智能分析 — 产品设计

> 状态：**已定稿归档**  
> 业务主体：冲焊装配供应商（可多租户）· 主用户：**采购部**  
> 关联：`docs/costing-engine-design.md`、`docs/l0-assembly-costing-design.md`、`docs/architecture.md`  
> 参考：仅借鉴「预聚合事实 + 强约束 Prompt」；不复用 Chat/SSE

**阅读指引**

| 章节 | 读者 | 内容 |
|------|------|------|
| **A. 产品契约** | 评审、采购、产品 | 用户看到什么、系统保证什么、禁止什么 |
| **B. 架构契约** | 后端、前端开发 | 分层边界、数据流、不可违反的工程规则 |
| **C. 实现附录** | 实现时查阅 | Schema 示例、API、目录、测试辅助 |

---

## A. 产品契约

### A.1 一句话

> **数字由系统计算，解释由 LLM 完成；采购约 30 秒从回答里抓住问题、关键数字与核对线索。问什么答什么，不铺报告模板。**

核价引擎是唯一算价真相源。LLM **不得**重算单价、改公式、自行汇总环比/占比/贡献度。

本产品本质：

> **基于核价结果库的分析查询系统 + LLM 自然语言解释层。**

### A.2 用户路径

```text
用户提问（或点胶囊）
    → 异步分析（轮询，无流式）
    → 聊天区展示 Markdown 正文
    → 可选：打印/Word 导出、分析历史重开
```

用户**不选**报表类型、Overview/Analyze/Drilldown、分析 mode 菜单。系统从问句推出内部 `analyses[]`（见附录 C.2）。

### A.3 聊天区：展示与不展示

| 展示 | 不展示 |
|------|--------|
| 用户问句 + 助理 **Markdown 正文** | Snapshot JSON、KPI 面板、图表 |
| 进行中 / 失败状态 | 跳转列表 Action、深链 query |
| 单条 **打印 / Word 导出**（问句、scope、时间元信息） | `analyses[]` 选择器、三 mode 菜单 |
| **分析历史** overlay（本人的记录，10 条/页，触底加载） | 流式打字机 |

**口径（tight/loose）**：写在 **Markdown 正文**里说明；**不做**单独口径徽章或证据抽屉（与「问什么答什么」一致）。

### A.4 分析历史与权限

| 规则 | 说明 |
|------|------|
| 权威存储 | 服务端 `llm_analysis_reports`，按 `user_id` 隔离 |
| 列表 | 所有人（**含管理员**）仅自己的记录；`GET /api/llm/reports`，默认每页 10 条，overlay **触底加载** |
| 详情 | 只能查看本人的记录；他人 **403** |
| 删除 | 只能删除本人的记录；管理员也不能删他人 |
| 本机缓存 | `localStorage`（`llm_chat_v1`）仅浮窗会话缓存；清缓存不删服务端记录 |

### A.5 验收口诀

> **30 秒内 Markdown 能指出一个问题，并给出可核对的关键数字/月份/零件；口径不可比时正文必须写清。**

| 场景 | 通过 | 失败 |
|------|------|------|
| 趋势 | 区间一次查询 + Analysis 环比与库一致 + 正文写明 tight/loose | 循环按月取数 / 模型自己算数 / 隐瞒 BOM 变更 |
| 动因 | TopN 数字出自 Analysis，正文引用 | 模型估算涨幅 |
| 跨基地 | comparison 结论在正文写清两侧差异 | 明细堆给模型自行比 |
| 单号 | drilldown+trend 同次分析，无无关空块 | 塞满无关 gate/parts |
| 聊天 UI | 仅 Markdown + 导出/历史 | 双轨 UI、证据面板、Action 按钮 |
| 帮助 | `usage_help` 命中 helper 语料 | 编造菜单路径 |
| 历史 | 服务端重开；本人列表/查看/删除 | 仅浏览器存储 |

### A.6 非目标

Tool Calling 开放域、流式打字机、侧栏分析菜单、自动议价发函、向量 RAG（首期）、LLM 算环比、聊天区 Snapshot 面板、跳转深链 Action、全站审计混进助理历史。

---

## B. 架构契约

### B.1 数据流（主图）

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
                  Repository        ← 查：WHERE / GROUP BY / SUM
                       │
                       ▼
                   Analysis          ← 算：MoM / TopN / 对比 / 异常
                       │
                       ▼
                AnalysisSnapshot      ← 本次确定性结果（生成态，仅喂 Prompt）
                       │
                       ▼
                      LLM            ← 解释与判断 → Markdown
                       │
                       ▼
              落库 + 聊天区 UI（仅正文）
```

**Snapshot 不整包暴露给聊天 API/UI**；采购只见 `markdown_content` 与元数据。

### B.2 四层职责

| 层 | 做 | 不做 |
|----|-----|------|
| **Query** | 结构化范围、口径、`analyses[]` | 不算金额；**意图由 Python 规则定** |
| **Repository** | 时间范围内事实与 SQL 查询聚合 | 业务分析（MoM、贡献度、议价判断） |
| **Analysis** | 趋势/对比/动因/异常等确定性结论 | 调 LLM；不绕过 Repo 写 SQL |
| **LLM + UI** | 写 Markdown；UI 只渲染正文 | 发明数字；挂证据抽屉 |

依赖：`llm` 为独立下游切片；可只读上游结果表 Model；分析主数据不经上游 Service→VO 拼装。

### B.3 Query：两层，避免 OLAP 膨胀

**Scope（查什么）**：`time_range` + `filters`（开放字典）+ `subject` + `comparison_basis`  
**Intent（做什么）**：`analyses[]`（可组合，非用户菜单）

不在 Schema 根上无限加 `supplier` / `thickness` 等字段；新维度进 `filters`。

**Parser 分工**（详见附录 C.4）：

| 谁 | 职责 |
|----|------|
| LLM（可选） | 仅抽 `time_range` / `filters`；无 key 时规则回退 |
| Python | 词典对齐、`analyses` / `subject` / `comparison_basis` |
| SQL/Repo | 精确取数 |

禁止：LLM 定意图、Parser 内算金额、Parser 内循环调 Service 取数。

### B.4 Repository ↔ Analysis 边界

```text
Repository                          Analysis
WHERE / JOIN / GROUP BY / SUM       MoM / YoY / 累计涨幅
BETWEEN start AND end               贡献度、TopN、异常判定
权限过滤                            跨基地对比结论、口径对齐后的差分
```

**时间范围**：一次按起止条件查询；**禁止**按月循环调上游 Service。

### B.5 可比口径 `comparison_basis`

时间相同 ≠ 可直接比。BOM/材料/工艺/公式版本变化时，「涨 8%」可能是对象变了。

- Analysis 输出 `comparability: tight | loose` 及原因  
- Snapshot.meta 记录口径标签  
- LLM 须在正文说明；loose 时不得宣称「纯价格上涨」  
- P0 至少：`same_part` + `same_bom_version`；材料/工艺可先占位

### B.6 Analysis 模块（按 `analyses[]` 按需执行）

| 模块 | 输出（确定性，LLM 不得改数） |
|------|------------------------------|
| `summary` | 盘子、结构、缺价计数 |
| `trend` | 序列、环比、累计变化、异常月 |
| `drivers` | TopN、change_rate、贡献度 |
| `comparison` | 跨基地/区间涨幅与差值 |
| `risk` | 缺价 / partial / gate |
| `drilldown` | 单号分解与区间差分 |

### B.6.1 核心算法公式（开发按此写，QA 按此验）

| 模块 | 输出字段 | 计算公式 / 判定规则（明确到边界条件） |
|------|---------|--------------------------------------|
| **trend.环比** | `mom_rate` | `(本月值 - 上月值) / 上月值`；**上月值=0 或 null → mom_rate = null**（不捏造 0% 或 ∞） |
| **trend.累计变化** | `cumulative_rate` | `(期末值 - 期初值) / 期初值`；期初值=0 → null |
| **trend.异常月** | `anomaly_months[]` | 满足以下任一条件即标记：① `abs(mom_rate) > avg(abs(mom_rate)) + 2*stddev`；② `abs(mom_rate) > 0.15`（15% 阈值）；命中则在 `meta.anomaly_note` 中说明 |
| **drivers.TopN** | `top_items[]` | 按 `abs(变化金额)` 降序取前 N（默认 5）；N 由 `filters.top_n` 控制或规则层默认 |
| **drivers.贡献度** | `contribution` | `该零件变化金额 / sum(所有变化金额绝对值)`；输出百分比及累计贡献（Top5 累计通常 >60% 才写「集中」，否则写「分散」） |
| **comparison.涨幅差** | `spread` | `(A终 - A初)/A初 - (B终 - B初)/B初`；任何分母=0 则该组比较结果标 `invalid`，不在正文中做量化对比 |
| **risk.缺价** | `missing_price_items[]` | 结果表中 `price IS NULL OR price = 0` 的记录，按零件号去重计数；不计入成本总额（Analysis 做 sum 时自动过滤这些行，且 meta 中写明过滤了多少条） |

> **开发约束**：所有数值保留 2 位小数（金额）或 2 位百分比（涨幅）；LLM Prompt 中禁止重新格式化单位（元→万元）。

### B.7 工程约束（合并清单）

| # | 约束 |
|---|------|
| 1 | 纯 REST + 异步轮询；无 SSE |
| 2 | 不改核价公式；金额单位「元」 |
| 3 | 业务分析只在 Analysis；Repository 仅查询聚合 |
| 4 | 时间范围一等公民；禁止按月循环 Service |
| 5 | `llm` 只读 Repo 直读结果表；遵守数据权限与口径 |
| 6 | Query = Scope + Intent；禁止根级字段森林 |
| 7 | 趋势/对比必带 `comparison_basis`；loose 写进 Markdown |
| 8 | Snapshot 只含本次 `analyses` 结果；禁止万能空块 |
| 9 | 分析类型 Python 规则组合；禁止三 mode 用户菜单 |
| 10 | 聊天区仅 Markdown；无 Action / 证据面板 |
| 11 | 帮助走 `usage_help` + `static/helper` 语料 |
| 12 | 分析历史落服务端；本人列表/查看/删除；localStorage 仅会话缓存 |
| 13 | 轻量 Parser；不做完备 NL Query Engine |
| 14 | **预聚合事实表优先**：Repository 优先查询按月/基地/车型预聚合的汇总表（如 `monthly_cost_summary`），不直接查明细 `l0_assembly_cost_detail`（除非 drilldown 单号）。预聚合表每日 ETL 凌晨更新，延迟 ≤ 24h。若预聚合表未就绪，自动降级到明细表但加 `/*+ MAX_EXECUTION_TIME(5000) */` Hint；**保护数据库不因全表扫描挂掉** |
| 15 | **超时与限流**：SQL 执行超过 5 秒自动熔断，返回 `data_message="当前数据量较大，建议缩小时间范围（如近3个月）"`；单用户并发任务 ≤ 2 个，超出返回 429（`too many requests`）；**保护系统不被偶然的「今年1月到8月」大查询拖垮** |

### B.8 P0 上线范围

首期必须交付、可对外使用的最小闭环：

| 能力 | 范围 |
|------|------|
| **入口** | 浮动助理；`user_question` 一问一答；胶囊人话；异步轮询 |
| **Query** | Parser（LLM 抽条件 + 词典对齐 + 规则定 `analyses[]`）；四级降级（C.4.2.1）；`usage_help` |
| **取数与算** | Repository 区间一次查询；Analysis `summary` / `trend` / `risk`（公式见 B.6.1）；`comparison_basis` 最小集（`same_part` + `same_bom_version`） |
| **输出** | 瘦 Snapshot → LLM Markdown；聊天区仅正文；口径 tight/loose 写在正文 |
| **持久化** | `llm_analysis_reports` 落库；本人列表/查看/删除；10 条/页触底加载 |
| **韧性** | LLM 失败 fallback 模板；SQL 熔断与单用户并发限流（B.7 #14/#15） |

**P0 不含**：打印/Word 导出、`comparison`/`drilldown` 组合深化、材料/工艺/公式版本口径校验、管理端审计、预聚合 ETL（可先查明细表 + 熔断，见 C.10 Story 1 可并行）。

---

## C. 实现附录

### C.1 AnalysisQuery 示例

```json
{
  "time_range": { "start": "2026-01", "end": "2026-08" },
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
  "analyses": ["summary", "trend"],
  "user_question": "今年青岛 T28 采购成本怎么变化？"
}
```

| 字段 | 说明 |
|------|------|
| `time_range` | `YYYY-MM`；单月 start=end |
| `filters` | 开放字典；口语经词典对齐后进此（附录 C.4.3） |
| `subject` | `cost_total` / `steel_price` / `part` / `l0` / … |
| `comparison_basis` | 见 C.3 |
| `analyses` | 见 C.2 |

问法 → 内部分组合示例：

| 用户问法 | `analyses`（示例） |
|----------|-------------------|
| 这个月采购成本怎么样？ | `summary`, `risk` |
| 今年青岛 T28 成本怎么变化？ | `summary`, `trend` |
| 哪些零件涨得最快？ | `drivers`, `trend` |
| 青岛和芜湖谁涨得更多？ | `comparison` |
| 501006875AA 为什么涨？ | `drilldown`, `trend`, `drivers` |

### C.2 `analyses` 枚举

| 值 | 含义 |
|----|------|
| `summary` | 盘子/结构/缺价计数 |
| `trend` | 时间序列趋势 |
| `drivers` | 涨跌动因 TopN |
| `comparison` | 跨基地/跨区间对比 |
| `risk` | 缺价 / partial / gate |
| `drilldown` | 单号分解（常配合 `filters.part_number`） |

规则层默认追加逻辑（附录 C.4.4）：默认 `summary`；跨月/趋势词 → `trend`；零件号 → `drilldown`；对比/多基地 → `comparison`；缺价 → `risk`。

### C.3 `comparison_basis` 字段

```json
{
  "comparison_basis": {
    "same_part": true,
    "same_bom_version": true,
    "same_material": true,
    "same_process": true,
    "same_formula_version": false,
    "label": "same_part_bom_material_process",
    "notes": "材料/工艺未对齐时不得宣称纯价格上涨"
  }
}
```

### C.4 Query Parser

#### C.4.1 流水线

```text
POST body：仅 user_question
        │
        ▼
 ConditionExtractor（LLM，t=0，可无 key 则规则回退）
        │  只吐 time_range / filters
        ▼
 EntityAligner（Python）「青岛厂」→ location:"青岛"
        │
        ▼
 QueryParser 规则 → analyses / subject / basis → AnalysisQuery
```

#### C.4.2 LLM 抽取契约

```json
{
  "time_range": { "start": "2026-01", "end": "2026-08" },
  "filters": { "location": "青岛厂", "vehicle_model": "T28" },
  "compare_locations": []
}
```

- 不得输出金额、结论、`analyses`  
- 未提时间 → 默认当前年月  
- 相对时间归一：这个月 / 近三个月 / 今年以来 / 过去半年（规则层校正）

#### C.4.2.1 降级链条（按顺序尝试，永远不报「解析失败」）

```text
第1级（最优）：LLM 成功抽取 → 词典对齐通过 → 使用
    │
第2级（部分降级）：LLM 抽取成功，但某 filter 对齐失败
    → 丢弃该 filter（不加），meta.unresolved_mentions 记录原文
    → 继续执行分析（范围放宽，而非中断）
    │
第3级（时间降级）：LLM 未抽/抽错 time_range
    → 规则层兜底：start = end = 当前系统月份
    → meta.data_message = "未识别到时间范围，默认分析当月"
    │
第4级（最粗兜底）：LLM 返回非 JSON / 超时 / 字段全缺
    → 全部规则兜底：
       time_range = 当前月份
       filters = {}（全量分析，不加任何基地/车型过滤）
       analyses = ["summary", "risk"]（最保守的安全组合）
    → meta.data_message = "未能识别具体条件，展示全量数据摘要"
    → 状态仍返回 success（不弹红字报错）
```

**原则**：让采购**永远看到一段 Markdown**（哪怕只是全量摘要），而不是「解析失败，请重新提问」。采购宁愿看到范围偏大的数据，也不愿意面对一个红色报错框。

#### C.4.3 词典对齐

| 步骤 | 做法 |
|------|------|
| 词典来源 | `scope_options_repository` DISTINCT + 别名表 |
| 对齐 | 精确 → 别名 → 去后缀「厂/基地」；禁止模糊错配 |
| 失败 | filter 不写入；`unresolved_mentions` 记入 meta |

#### C.4.4 `analyses` 规则表

| 线索 | 追加 |
|------|------|
| 默认 | `summary` |
| 跨月 / 趋势 / 涨跌 | `trend` |
| 零件号 | `drilldown` |
| 对比 / 谁更 / 多基地 | `comparison` |
| 缺价 / partial | `risk` |

帮助类问句走 `usage_help`，语料 `static/helper/*.html`，不查核价库。

### C.5 AnalysisSnapshot 形状

> 生成态；按需填充；只含本次 `analyses` 请求的部分。

```json
{
  "query": { },
  "meta": {
    "has_data": true,
    "comparability": "tight",
    "comparison_basis_label": "same_part_and_bom",
    "currency_note": "金额单位：元",
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

`result.kind` 可为 `trend` | `drivers` | `comparison` | `risk` | `drilldown` | `composite`。  
`composite` 时 `result.parts` 仅含本次请求的子模块。

喂 Prompt：System（禁止重算、loose 必说明）+ User（`user_question` + 裁剪后 Snapshot JSON）。

#### C.5.1 可观测性（生产必配）

| 项 | 落点 | 用途 |
|----|------|------|
| `trace_id` | 每个任务生成一个 UUID，贯穿 Query → Repo → Analysis → LLM，写进 `llm_analysis_reports.trace_id` | 线上排查单个分析请求的全链路耗时 |
| **LLM 输入输出审计** | 记录 `prompt_preview`（前 500 字符）和 `llm_response_preview`（前 500 字符），落库但不返回前端 | 调试抽取不准 / 回答跑偏，回放现场 |
| **慢查询日志** | Repo 层 SQL 执行 > 1s 的打印 `warn` 日志，含 `trace_id` 和 SQL 摘要 | DBA 介入优化前，开发自己先抓到是哪条 SQL 慢 |
| **分析结果对比** | 每个 Snapshot 中 `analysis_version` 字段（如 `v1.0`），便于日后算法升级时回溯旧结果是否被影响 | 算法迭代时，有基线版本可对比 |

### C.6 HTTP API

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/llm/reports` | body：`user_question`（+ 可选 `audience` / `force_refresh` / `idempotency_key`） |
| `GET` | `/api/llm/tasks/{task_id}` | 轮询 |
| `GET` | `/api/llm/reports/{id}` | Markdown + 元数据；校验 `user_id` |
| `GET` | `/api/llm/reports` | 本人历史分页（默认 limit=10）；**列表项 VO**，不含 `markdown_content` |
| `DELETE` | `/api/llm/reports/{id}` | 只能删除本人的记录 |

```json
{
  "user_question": "2026年1月到8月，青岛采购成本怎么变化？",
  "force_refresh": false,
  "idempotency_key": null
}
```

对外不传 `scope` / `analyses[]`；由服务端解析组合。

**落库字段（`llm_analysis_reports`）**：`user_id`、`user_question`、scope 字段、`markdown_content`、状态、审计等。完整 Snapshot **不落库整包**。

### C.7 目录结构

```text
app/services/llm/
  query/                  # parser, condition_extractor, entity_aligner, time_range, comparison_basis
  analysis/               # summary, trend, driver, comparison, drilldown, runner
  context/                # snapshot_builder
  catalog/                # field_labels
  usage/                  # usage_help 语料检索
  generator.py
  report_service.py

app/repositories/llm/     # cost/steel/stamping analysis repos, scope_options, report_repository
app/schemas/llm/
app/routers/llm/
static/js/llm-assistant/
```

### C.8 `menu_catalog`（测试辅助）

**不进产品 UI。** 保留 `subject → hash_page` 映射，用于：

- `tests/llm/test_menu_questions.py` 菜单问句回归  
- 侧栏覆盖审计（`MENU_COVERAGE`）

| `subject` | 落点（参考） |
|-----------|--------------|
| `l0` / `cost_total` | `#/l0-assembly-cost` |
| `stamping_part` | `#/stamping-part-cost` |
| `steel_price` | `#/steel-price-list` |
| `steel_price_policy` | `#/steel-price-policy-download` |
| `steel_base_price` | `#/base-price-download` |

### C.9 Repository 示意

```python
def query_l0_monthly_totals(
    db: Session,
    *,
    filters: dict[str, str],
    start: str,  # YYYY-MM
    end: str,
    tenant_id: ...,
) -> list[MonthlyTotalRow]:
    """WHERE + GROUP BY month + SUM；不含环比/贡献度。"""
```

禁止：Repository 方法名 `analyze_*`；Repo 内 MoM/议价判断；Analysis 内绕过 Repo 的 SQL。

### C.10 开发拆单指南（按此拆 Story）

| 序号 | Story 名称 | 产出 | 预估（人天） |
|------|-----------|------|-------------|
| 1 | **预聚合表 ETL** | 新建 `monthly_cost_summary` 表 + 每日定时任务（凌晨 2 点） | 2 |
| 2 | **Repository 层** | `query_monthly_totals`、`query_part_details`、`query_location_comparison` 三个方法 + 单元测试（Mock DB） | 2 |
| 3 | **Analysis 核心算法** | `trend.py`、`drivers.py`、`comparison.py`、`risk.py`、`drilldown.py` + 公式单测（输入固定序列，输出预期数字） | 3 |
| 4 | **Query Parser** | `condition_extractor`（LLM 调用）+ `entity_aligner`（词典对齐）+ `analyses_rules` + 降级策略单测（模拟 LLM 失败场景） | 3 |
| 5 | **Snapshot + LLM 生成** | `snapshot_builder` + `generator.py`（Prompt 组装 + LLM 调用）+ Markdown 渲染校验 | 2 |
| 6 | **API + 落库 + 历史** | 5 个 HTTP 接口 + `llm_analysis_reports` 表迁移 + 权限校验（本人隔离） | 2 |
| 7 | **前端浮窗 + 历史 overlay** | 聊天区、胶囊、打印/Word 导出、历史列表（触底加载） | 3 |
| 8 | **联调与 50 条真实问句回归** | 拿采购部真实问句跑通，调 Prompt 直到 90% 以上可接受 | 2 |
| **合计** | | | **19 人天（≈ 1 人月）** |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-23 | **归档**：删 B.8 分期 / B.9 决策摘要，合并为 B.8 P0 上线范围 |
| 2026-08-23 | 施工补丁：B.6.1 算法公式、C.4.2.1 降级链条、B.7 #14/#15 性能约束、C.5.1 可观测性、C.10 拆单指南 |
| 2026-08-23 | **文档熵减**：重组为 A 产品 / B 架构 / C 附录；合并约束清单；口径统一为 Markdown 正文；历史本人+10条触底；移除 Action/三 mode 主叙事 |
| 2026-08-22 | 初稿：分析查询系统 + LLM 解释层；四层边界；时间范围与可比口径 |

---

*实现以 **A（产品）+ B（架构）** 为准；Schema/API 细节查 **C（附录）**。*
