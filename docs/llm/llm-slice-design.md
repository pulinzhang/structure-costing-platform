# LLM 垂直切片 — 设计说明

> 状态：**已上线（as-built）**  
> 读者：新加入本切片的开发  
> 产品契约（用户看到什么、禁止 LLM 算数）：[llm-costing-analysis-report-design.md](llm-costing-analysis-report-design.md)  
> 关联：`docs/architecture.md`、[核价引擎](../costing/costing-engine-design.md)  
> 现网：`app/routers/llm.py`、`app/services/llm/`、`app/repositories/llm/`、`static/js/llm-assistant/`、`tests/llm/`

**先读哪份**

| 你要做什么 | 读 |
|------------|----|
| 产品规则、公式、API 契约 | 产品契约（A / B / C） |
| 代码在哪、一次提问怎么走、改哪一层 | **本文** |
| 分层硬约束（上游不得 `import llm`） | `architecture.md` + 产品契约 B.2.1 |

---

## 1. 一句话说明

> **数字由 Python 在核价结果表上算出来，LLM 只把 Snapshot 写成中文 Markdown。**  
> 入口是顶栏浮动助理；异步轮询，无流式。帮助问句和「还差什么才能核算」走旁路，不查明细核价。  
> 挂在 **结构件自动核价平台**（小名：核价平台）上，核总成 / 分总成 / 冲压件。

---

## 2. 切片在平台里的位置

```text
上游：settings · stamping · bom · yishiyiyi · costing
本切片：llm（解释层，独立下游）
```

| 做 | 不做 |
|----|------|
| 只读上游 **结果表 Model**（明细直查） | 经上游 Service→VO 拼分析主数据 |
| 金额展示、年月键留在 `app/services/llm/_money.py` | 抽到 `app/common/` |
| 异步走公共 `async_task` | 写核价金额、改公式、建 LLM 专用汇总表 |
| 报告落 `llm_analysis_reports` | 上游切片 `import llm` |

---

## 3. 端到端流水线

```text
顶栏助理  POST /api/llm/reports  { user_question, previous_report_id? }
        │
        ▼
LlmAnalysisReportService.create_report
        │  QueryParser.parse（规则定 mode / subject / analyses[]）
        │  并发 ≤2 / 人；幂等命中则直接返回
        │  落库 pending + submit_session_worker
        ▼
_run_report_work（runner 提供任务 Session / 进度 / catch）
        │
        ├─ query_mode = usage_help        → UsageHelpRunner（helper 语料）
        ├─ query_mode = engine_readiness  → EngineReadinessRunner（CostingEngineService.get_ready）
        └─ query_mode = analysis          → AnalysisRunner（按 subject 分发）
                │
                ▼
        SnapshotBuilder.build
                │
                ▼
        LlmReportGenerator（Prompt + OpenAI 兼容 HTTP；失败则规则模板）
                │
                ▼
        落库 markdown_content；前端轮询 GET /api/llm/tasks/{task_id}
        聊天区只渲染 Markdown（Snapshot 不回前端）
```

编排入口只有 `LlmAnalysisReportService`。Router 不做分支。

---

## 4. 三种问句模式

`QueryParser` 里 **Python 规则**先定 `query_mode`（`intent_router.detect_query_mode`），**不由模型决定意图**。

| `query_mode` | 何时 | 取数 | 生成 |
|--------------|------|------|------|
| `analysis` | 默认；价格/趋势/一览/存在吗 | 本切片 Analysis Repo 查明细 | 受众 Prompt + Snapshot JSON |
| `usage_help` | 「怎么用 / 在哪 / 权限 / 卡住」等 | `static/helper` 语料，**不查核价库** | `system_usage_help.md` |
| `engine_readiness` | 「还差什么才能核算」 | 与引擎页同源 `get_ready` | 规则 Markdown（可不调模型） |

帮助与分析同时出现时：**有明确查数口语优先 analysis**；缺口词 + 核算词才进就绪。

---

## 5. Service 目录（`app/services/llm/`）

| 路径 | 职责 |
|------|------|
| `report_service.py` | 唯一编排：解析、限流、幂等、入队、落库、权限隔离 |
| `query/` | 问句 → `AnalysisQuery`（不 import analysis） |
| `analysis/` | 确定性分析（查库 + 公式）；只读 Query 字段与叶模块，不 import query |
| `_money.py` / `comparison_basis.py` | 切片叶模块：金额、移月、口径映射 |
| `context/snapshot_builder.py` | `AnalysisRunResult` → 喂 Prompt 的 Snapshot |
| `generator.py` | 拼 Prompt、调模型、失败 fallback |
| `prompts/` | `manifest.yaml` + 受众 system + `_shared` 铁律 |
| `client/` | OpenAI 兼容 HTTP（`LLM_BASE_URL` / `LLM_API_KEY`） |
| `usage/` | 帮助语料检索 |
| `engine_readiness/` | 核算就绪门禁快照 |
| `catalog/field_labels.py` | JSON 字段 → 中文释义卡 |
| `menu_catalog.py` | `subject → hash_page`；**不进产品 UI**，给测试覆盖审计 |
| `_money.py` | 金额字符串、年月键、移月；切片叶模块 |
| `comparison_basis.py` | tight/loose 映射；切片叶模块 |

包根 `__init__.py` 只作标记，不汇总导出。

---

## 6. Query：问句怎么变成结构化查询

流水线（产品契约 C.4）：

```text
user_question (+ 可选上一份报告的 AnalysisQuery)
    → ConditionExtractor（可选 LLM，只抽 time_range / filters）
    → EntityAligner（主数据词典对齐基地/项目）
    → 问句证据覆盖 + 缺槽沿用上一问范围
    → 规则：query_mode / subject / analyses[] / comparison_basis
    → AnalysisQuery
```

| 模块 | 文件 |
|------|------|
| 对外入口 | `query/query_parser.py`（re-export `QueryParser`） |
| 流水线 | `query/parser/pipeline.py` |
| 口语 → subject | `query/parser/subjects.py`（顺序即优先级） |
| analyses[] | `query/parser/analyses.py` |
| 问价 / 下钻 | `query/parser/part_price.py` |
| 草稿 / 钉月 | `query/parser/draft.py`、`pin_latest.py` |
| 上一问沿用 | `query/parser/carry.py` |
| 模式分流 | `query/intent_router.py` |
| 条件抽取 | `query/condition_extractor.py` |
| 词典对齐 | `query/entity_aligner.py` |
| 时间口语 | `query/time_range.py`（移月在 `_money.shift_month`） |
| 口径映射 | `comparison_basis.py`（叶模块，非 query） |

**Scope**（查什么）：`time_range` + `filters` 开放字典 + `subject` + `comparison_basis`。新维度进 `filters`，不要在 Schema 根上加字段森林。

**Intent**（做什么）：`analyses[]` = `summary` / `trend` / `drivers` / `comparison` / `risk` / `drilldown`。问价口语写入 `asks_part_price`，Analysis 只读该字段。用户看不到这组枚举。

解析失败走四级降级（产品契约 C.4.2.1），**永远返回一段 Markdown**，不弹「解析失败」。

---

## 7. Analysis：按主题分发，公式集中

对外：

```python
from app.services.llm.analysis.runner import AnalysisRunner, AnalysisRunResult
```

`AnalysisRunner` **只按 `query.subject` 分发**，自己不算 MoM、不写 SQL。

```text
AnalysisRunner
  OpsAnalysis         作业台 / 模具费 / 检具费 / 采购对象
  StampingAnalysis    工艺 / 冲次 / 加工费 / 冲压零件价
  SteelAnalysis       联动价 / 政策 / 基价 / 中标厚度 / 废料
  WeldingAnalysis     焊接单价 / 拆解 / 成品焊接费
  BomAnalysis         年价 / 包装运输 / 材料清单
  AssemblyAnalysis    成品核价 / 零件存在性 / 单件问价
```

`part` 与未匹配 subject 走 `AssemblyAnalysis`（单件问价或默认 L0）。

| 包 | 内容 |
|----|------|
| `analysis/runner.py` | 薄分发；对外 re-export `AnalysisRunResult` |
| `analysis/shared/` | 公式、口径、趋势/驱动/异常/下钻、`result.py`、`compose.py`；切片内部从此取 `AnalysisRunResult` |
| `analysis/{ops,stamping,steel,welding,bom,assembly}/` | 主题 `run.py` + 该主题 summary 函数 |

公式与边界条件（环比分母为 0、缺价不进趋势等）以产品契约 **B.6.1** 为准，实现在 `shared/formulas.py` 及对应 summary。**禁止**在主题 `run.py` 里新写一套环比。

包内 README：`app/services/llm/analysis/README.md`。

### 7.1 `subject` → 主题类（现网）

| `subject` | 类 | 对齐列表页（`menu_catalog`） |
|-----------|----|------------------------------|
| `ops_workbench` | Ops | 作业台 |
| `stamping_die_fee` / `stamping_gauge_fee` / `procurement_object` | Ops | 模具费 / 检具费 / 采购对象 |
| `stamping_process` / `stamping_tonnage` / `stamping_process_fee` / `stamping_part` | Stamping | 工艺 / 冲次 / 加工费 / 零件价 |
| `steel_price` / `steel_price_policy` / `steel_base_price` / `winning_thickness` / `scrap_price` | Steel | 联动价 / 政策 / 基价 / 中标厚度 / 废料 |
| `welding_unit_price` / `welding_process_breakdown` / `l0_welding_fee` | Welding | 焊接三张表 |
| `annual_part_price` / `packaging_transport_fee` / `bom_material` | Bom | 年价 / 包装运输 / 材料清单 |
| `part` | Assembly | 跨域存在性 / 问价 |
| `l0` / `cost_total` 及默认 | Assembly | `#/assembly-cost` |

加新实体列表问句：Parser 认 subject → 主题 `run.py` 一条方法 → 本切片 Analysis Repository（或下游 Analysis 调上游 Service）→ `menu_catalog` 覆盖项 → `tests/llm` 问句回归。

中标厚度：`SteelAnalysis` 调上游 `WinningThicknessExportService`（宪法允许下游 Service 组合上游）。**禁止**再经 `repositories/llm` 转发 VO。

`ANALYSIS_VERSION` 定义在 `schemas/llm/analysis_snapshot.py`；Analysis 只引用，Schema 不 import Service。

Markdown 清洗在 `generator`（写入前）和 `report_service._report_vo`（读出时），不在 VO。

---

## 8. Repository（`app/repositories/llm/`）

只做 `WHERE / JOIN / GROUP BY / SUM`。环比、TopN、异常判定在 Analysis。

| 模块 | 用途 |
|------|------|
| `cost_analysis/` | 总成核价只读。SQL 在 `monthly_totals` / `part_rows` / `card` / `composition`；`L0CostAnalysisRepository` 只转发 |
| `stamping_*` / `process_fee_*` / `die_fee_*` / `gauge_fee_*` / `tonnage_*` | 冲压路径 |
| `steel_price_*` / `policy_*` / `base_price_*` / `scrap_price_*` | 钢价与一事一议（中标厚度不经本切片 Repo，见 §7） |
| `welding_*` / `l0_welding_fee_*` | 焊接 |
| `annual_part_price_*` / `packaging_transport_*` / `bom_material_*` / `procurement_object_*` | BOM |
| `ops_workbench_repository.py` | 作业台计数 |
| `scope_options_repository.py` | Parser 词典（基地/项目），禁止调 VehicleModelService |
| `report_repository.py` | 报告 CRUD / 幂等命中 |
| `_query_guard.py` | SQL >1s 打 warn（含 `trace_id`）；**无超时熔断** |

禁止：方法名 `analyze_*`；为 LLM 建预聚合表 / ETL。理由见产品契约 B.7.1。

---

## 9. Snapshot、Prompt、模型

```text
AnalysisRunResult  →  SnapshotBuilder  →  AnalysisSnapshot
                         │
                         ▼
              仅 to_prompt_dict() 进 User Prompt
              聊天 API 不返回 Snapshot 整包
```

| 模块 | 说明 |
|------|------|
| `prompts/manifest.yaml` | 版本、受众、shared 拼接顺序；**改文案须 bump version** |
| `prompts/system_*.md` | 受众人设（采购 / 主管 / 核价 / 销售 / 经营） |
| `prompts/_shared/*.md` | 中文、货币「元」、口径、异常、范围铁律 |
| `generator.py` | 分析走受众 Prompt；帮助走 usage；就绪可走规则模板 |
| `client/openai_compatible.py` | `settings.LLM_*` |

LLM 调用失败：`render_fallback_markdown`，任务仍 **succeeded**（采购看到规则摘要，不是红字）。

---

## 10. HTTP、落库、前端、权限

### 10.1 API

`app/routers/llm.py`，前缀 `/api/llm`。

| Method | Path | 权限 |
|--------|------|------|
| `POST` | `/reports` | `op:llm-analysis:run` |
| `GET` | `/tasks/{task_id}` | `op:llm-analysis:view` |
| `GET` | `/reports` | 本人分页，列表 **无** `markdown_content` |
| `GET` | `/reports/{id}` | 本人详情 |
| `DELETE` | `/reports/{id}` | 只能删本人（管理员也不能删他人） |

Body：`user_question`（可选 `audience` / `force_refresh` / `idempotency_key` / `previous_report_id`）。不传 `analyses[]`。`previous_report_id` 无效则当无上一问。

### 10.2 表

`llm_analysis_reports`：问句、scope 占位字段、`query_json`（解析结果，供下一问沿用）、Markdown、状态、`trace_id`、prompt 预览。**不落 Snapshot 整包。** 通过 `task_id` 挂公共异步任务。

### 10.3 前端

| 路径 | 职责 |
|------|------|
| `static/js/llm-assistant/` | 顶栏入口、浮窗、胶囊、轮询、历史 overlay、打印/Word |
| `static/llm-analysis-report.html` | 单条报告打印页 |
| `localStorage` `llm_chat_v1` | 仅会话缓存；清缓存不删服务端记录 |

无侧栏「分析类型」菜单；无 SSE。

### 10.4 权限

| 码 | 含义 |
|----|------|
| `menu:llm-analysis` | 菜单（若启用） |
| `op:llm-analysis:view` | 看自己的报告 / 轮询 |
| `op:llm-analysis:run` | 提交分析 |

无权限则顶栏不注入入口。树以 `catalog.json` 为准。

### 10.5 配置

| 项 | 含义 |
|----|------|
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | 模型 HTTP |
| `LLM_TIMEOUT_SECONDS` | 默认 90 |
| `LLM_MAX_CONCURRENT_TASKS_PER_USER` | 默认 2，超出 429 |
| `LLM_IDEMPOTENCY_TTL_MINUTES` | 默认 5 |

---

## 11. 硬约束（实现时对照）

与产品契约 B.7 一致，新人改代码时优先守这几条：

1. 数字只出 Analysis；LLM 禁止重算、禁止改成万元。  
2. Repo 只查询聚合；Analysis 不算 SQL。  
3. 时间范围一次 `WHERE`；禁止按月循环调上游 Service。  
4. 禁止 LLM 专用预聚合表 / ETL。  
5. 内部工具不进 `app/common`；上游不得 `import llm`。  
6. 聊天区只展示 Markdown。  
7. 意图由 Python 定，不由模型定 `analyses[]`。

---

## 12. 新人改需求时去哪

| 需求 | 改这里 | 不要改 |
|------|--------|--------|
| 新问法仍落已有列表页 | `query/parser/subjects.py` | 不要让 LLM 输出 subject |
| 新实体表可问 | Parser + 主题 `run.py` + Analysis Repo + `menu_catalog` + 测试 | 不要塞进 `AnalysisRunner.run` 长 if |
| 环比/缺价口径 | `analysis/shared/` + 产品契约 B.6.1 | 不要在主题 run 里复制公式 |
| 回答口吻 / 禁止事项 | `prompts/`（bump `manifest.yaml` version） | 不要在 Generator 里写死长文案 |
| 帮助「怎么点菜单」 | `usage/` + `static/helper` | 不要去查核价表 |
| 核算缺口口径 | `engine_readiness/`；须与引擎 `get_ready` 同源 | 不要自己发明红灯 |
| 限流 / 幂等 | `report_service.py` + `settings` | — |
| 浮窗交互 | `static/js/llm-assistant/`（改脚本递增 `?v=`） | 不要在聊天区挂 Snapshot JSON |

---

## 13. 相关代码锚点

| 主题 | 路径 |
|------|------|
| HTTP | `app/routers/llm.py` |
| 编排 | `app/services/llm/report_service.py` |
| Query | `app/services/llm/query/`（规则在 `query/parser/`） |
| Analysis 分发 | `app/services/llm/analysis/runner.py` |
| 公式与口径 | `app/services/llm/analysis/shared/` |
| Snapshot | `app/services/llm/context/snapshot_builder.py` |
| Prompt / 模型 | `app/services/llm/generator.py`、`prompts/`、`client/` |
| 报告表 | `app/models/llm/analysis_report.py`、`app/repositories/llm/report_repository.py` |
| Schema | `app/schemas/llm/` |
| 前端 | `static/js/llm-assistant/` |
| 测试 | `tests/llm/`（集成标 `@pytest.mark.integration`） |
| 脚本 | `scripts/llm_*.py` |

---

## 14. 测试建议

| 类型 | 场景 |
|------|------|
| 公式 | `test_analysis_formulas.py`：分母为 0、单月累计变化为 null |
| Parser | 口语 → subject / analyses / query_mode；帮助 vs 查数 vs 就绪 |
| 分发 | `test_menu_entity_audit.py`：实体列表 subject 都在 `AnalysisRunner._handlers` |
| 问价 | 核价表材料行优先、年价兜底（`test_leaf_part_price.py`） |
| 权限 | 不能看/删他人报告 |
| 并发 | 第三人任务 429 |
| 集成 | 真实库问句（`not integration` 的 CI 默认跳过） |

本地：`python -X utf8 -m pytest tests/llm -m "not integration"`。

---

## 15. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-12 | QueryParser 拆到 `query/parser/`：subject / analyses 与流水线分离 |
| 2026-09-12 | 初稿：as-built 切片导读；Analysis 按主题分包后的目录与分发 |
| 2026-09-20 | 采购对象：费用混淆走 `faq_procurement_fee`；操作员/主管场景规则；缺供应商进 risk |
| 2026-09-20 | 核价概况旁挂 `period_discontinue`（完成停止/此件不装），解释件数变少不是算错 |
| 2026-09-20 | 管理人员 EC×核价：自然语言生效月 FAQ；`ec_procurement_supplier`；核价强制旁挂 `period_missing_supplier`；价差涨超10%/构成；下游齐套与工艺布点到期 |
| 2026-09-20 | 工程变更：变更前/后零件单价比较（总成应成本优先，冲压单价兜底） |
