# 成品月核价 Service（`costing/assembly_cost`）

> costing 下游切片 · 成品（总成）月核价业务层  
> 路径：`app/services/costing/assembly_cost/`  
> 口径与表结构：[`docs/costing/assembly-costing-design.md`](../../../../docs/costing/assembly-costing-design.md)

| 模块 | 职责 |
|------|------|
| `service.py` | 列表分页、计算入队、委托编排器 |
| `audit/service.py` | 范围删除 / 审核 / 反审核 |
| `calc/orchestrator/` | 齐套检查与一次计算：prepare → engine → persist |
| `export/` | 已落库结果表 Excel |
| `calc_report/` | 计算日志过程报告 Excel（禁止 import `export/`） |
| `restore/` | 核价卡还原 |

下文是目录与数据流附录。

---

本目录是 **Service 垂直包**：列表/审核、异步计算、结果表 Excel、计算过程报告。  
Repository / Model / Router / Schema 不在这里。

不要再开 `app/services/costing/report/`。报告是本切片计算日志的一种视图，不是新的限界上下文。

---

## 1. 业务范围

| 能力 | 落点 | 说明 |
|------|------|------|
| 列表 / 明细 | `service.py` | 财务 / 采购视图筛选项不同 |
| 审核 / 删除 | `audit/service.py` | 范围删除、审核、反审核；门面委托 |
| 计算就绪 / 入队 / worker | `service.py` → `calc/` | 锁 scope、异步任务、委托编排器 |
| 逐卡 rollup | `calc/rollup.py` + `calc/orchestrator/` | 指挥家只编排，不算账 |
| 计算日志 | `calc/calc_log.py` + `process_log.py` | 给人看的过程 + 可筛选核价卡 JSON |
| 结果表 Excel | `export/` | 财务对账册 / 采购零件成本册；月度核对导出可叠 Sheet |
| 过程报告 Excel | `calc_report/` | 与浅色报告页同口径；数据来自计算日志，不是结果表 |

**Router 入口（按职责拆文件，类名保持稳定）：**

```python
from app.services.costing.assembly_cost.service import AssemblyCostService
from app.services.costing.assembly_cost.export.service import (
    AssemblyCostExportService,
)
from app.services.costing.assembly_cost.calc_report.service import (
    AssemblyCostCalcReportExportService,
)
```

| HTTP | 权限（示意） |
|------|----------------|
| `GET/PATCH/DELETE /api/costing/assembly-costs` | `op:assembly-cost:*` |
| `GET …/export-download?view=finance\|procurement` | `op:assembly-cost:export` |
| `POST …/calc`、日志 CRUD | `op:assembly-cost-calc:*` |
| `GET …/calc/logs/{id}/export-download` | 计算日志附件，仍走 calc Router |

月度核对导出：`GET /api/costing/monthly-bundle/export-download`（**无** `view`）调用  
`AssemblyCostExportService.write_to_workbook(..., view="finance")`，只叠树根成品块。

---

## 2. 为什么这样组织

1. **门面与计算拆开**  
   列表/审核不塞进编排器；计算不经过列表 VO 再算一遍。

2. **两种 Excel 是两种产品**  
   `export/` = 已落库结果表（对账）。`calc_report/` = 某次计算日志（过程）。禁止互相 import。

3. **短码无归属切片、两边都要用**  
   `codes.py` 只有纯函数、无 ORM。焊费卡 ID 收集依赖 `AssemblyCost`，留在 `export/workbook/builder.py`。

4. **指挥家宪法**  
   `calc/orchestrator/orchestrator.py` 主路径只有 `prepare → engine.run → persist`。循环、写库、拼过程文案不进该文件。

5. **月度核对导出合同**  
   保留 `write_to_workbook(wb, db, …)`，月度核对导出和其他切片同一套叠 Sheet。不要改成只返回 bytes。

---

## 3. 目录结构

```text
assembly_cost/
├── README.md                         # 本说明
├── __init__.py                       # 包标记（不汇总导出）
├── service.py                          # HTTP 门面：列表 + 审核委托 + 计算委托
├── audit/service.py                    # 范围删除 / 审核 / 反审核
├── codes.py                          # part_short_code / item_short_code
├── calc/
│   ├── __init__.py                   # 只作包标记，不汇总导出
│   ├── rollup.py                     # 单卡金额公式
│   ├── process_log.py                # 过程说明 / 核价卡 JSON 形态
│   ├── calc_log.py                   # 计算日志 + scope 锁
│   └── orchestrator/
│       ├── orchestrator.py           # 指挥：prepare → engine → persist
│       ├── deps.py                   # 编排依赖装配
│       ├── ready.py                  # 计算前上游是否齐
│       ├── prep.py                   # 拉 BOM / 价表
│       ├── batch_engine.py           # 逐卡 rollup + SAVEPOINT
│       ├── persist.py                # 提交结果、写日志终态
│       └── progress.py               # 进度回调适配
├── export/                           # 结果表工作簿
│   ├── __init__.py
│   ├── service.py                    # 筛选校验、文件名、水印 bytes
│   └── workbook/                     # 列 / 样式 / 各 Sheet（openpyxl）
│       ├── builder.py                # 取数 + 写 Sheet；collect_welding_fee_ids
│       ├── columns.py / labels.py / layout.py / styles.py / filename.py
│       ├── list_sheet.py / items_sheet.py / indirects_sheet.py
│       └── （焊费 Sheet 委托 BomWeldingFeeExportService.write_to_workbook）
└── calc_report/                      # 计算过程报告工作簿
    ├── service.py                    # 拉日志、筛卡、文件名、水印 bytes
    ├── builder.py                    # CalcReportWorkbookBuilder
    ├── match.py                      # 与浅色页筛选同口径
    ├── columns.py / labels.py / layout.py / styles.py / filename.py
    └── cover_sheet.py / cards_sheet.py / narrative_sheet.py
```

| 文件 / 包 | 负责 | 不负责 |
|-----------|------|--------|
| `service.py` | 分页 VO、`start_calc`、把计算交给 orchestrator；审核委托 `audit/` | 单元格、rollup 循环 |
| `audit/service.py` | 范围删除 / 审核 / 反审核 | 列表、计算 |
| `codes.py` | 零件/子件短码规则 | 查库 |
| `calc/rollup.py` | 单卡公式 | Session、Excel |
| `calc/orchestrator/` | 一次计算的编排与落库 | HTTP、xlsx 版式 |
| `export/` | 结果表对账册 | 计算日志 |
| `calc_report/` | 日志浅色报告 Excel | 结果表、月度核对导出 |

`export/` 与 `calc_report/` 各自有一套 `styles.py`：财务核对偏深色工业表，过程报告偏浅色阅读页。不要合成一份色板。

---

## 4. 依赖方向

```text
Router costing/assembly_cost/crud.py
  ├── AssemblyCostService
  └── AssemblyCostExportService
        └── workbook.builder（Repository + Sheet 写入）
              └── codes.py
              └── BomWeldingFeeExportService.write_to_workbook（按 welding_fee_id）

Router costing/assembly_cost/calc.py
  ├── AssemblyCostService → calc.orchestrator
  │                            ├── prep / ready / deps
  │                            ├── BatchCalculationEngine → rollup + process_log
  │                            └── persist + calc_log.py
  └── AssemblyCostCalcReportExportService
        └── calc_report.builder（只读 CalcLog VO）
              └── codes.py
              └── calc_report.match

monthly_bundle_export
  └── AssemblyCostExportService.write_to_workbook(view="finance")
```

**允许**

- `export` / `calc_report` → `codes.py`
- `calc_report` → `calc.calc_log`（读日志）
- `export.workbook.builder` → 本切片 / 上游只读 Repository
- 下游月度核对导出 → `export` 的 `write_to_workbook`

**禁止**

- `calc_report` import `export`，或反过来
- `codes.py` import Model / Repository
- `calc/orchestrator/orchestrator.py` 主方法里 `for` / 写库 / 拼过程文案
- Router 直接调 `workbook.builder` / Repository / Parser
- 把过程报告抽到别的 costing 切片

---

## 5. 数据流（三条主路径）

### 5.1 计算

```text
CalcDTO
  → 建 processing 日志 + scope 锁
  → prepare_calc_run（BOM 树、冲压价、年度价、焊费、包装…）
  → BatchCalculationEngine.run（逐卡 rollup_assembly）
  → persist_calc_result（主表 / items / indirects + 日志终态）
```

### 5.2 结果表导出

```text
筛选（财务至少一项；采购必须锁年/月/基地/车型/BOM 版本）
  → Repository 列表
  → 一览 / 材料明细 / 焊费（卡上的 welding_fee_id，不是 level=0）
  → 财务另写间接费 Sheet；采购不写间接、不含报价/价差列
  → 一览表头合计 + 表外 SUM 行（不进筛选）：采购为本册对象；财务为本表树根
  → 水印 bytes + 文件名
```

子件短码：仅 `cost_source == "stamping"` 时截码；标准件 / 年度价留空。焊费金额 0 导出为空单元格。采购一览合计是对象卡全量，不是整车月总账。财务一览合计是当前导出范围内的树根，筛选条件碎时不要当成整车账。

### 5.3 过程报告

```text
log_id + keyword/status/level/tree_root
  → get_calc_log
  → match_calc_report_card
  → 封面 / 核价卡 / 过程说明
```

独立浅色页：`/assembly-cost-calc-report?log_id=`，脚本是 `features/costing/assembly-cost/calc-report/boot.js`（**不要**做成 SPA 的 `index.js` `pageConfig`）。URL 与权限不随目录搬家而改。

---

## 6. 职责

| 模块 | 职责 |
|------|------|
| `service.py` + Repository | 列表筛选项、审核 |
| `calc/rollup.py` | 单卡公式、公式版本号 |
| `orchestrator/ready.py` / `prep.py` | 上游是否齐、拉哪些价表 |
| `batch_engine.py` | 逐卡落库、SAVEPOINT |
| `process_log.py` | 过程文案 / 核价卡 JSON |
| `export/workbook/columns.py` | 结果表列、财务 vs 采购 Sheet 名 |
| 对应 `*_sheet.py` + `codes.py` | 结果表取值、短码、焊费 ID |
| `write_to_workbook` + `monthly_bundle_export` | 月度核对导出叠哪些成品 Sheet |
| `calc_report/match.py` | 报告筛选口径（与浅色页同一套） |
| `calc_report/columns.py` / `labels.py` / `*_sheet.py` | 报告列 / 封面文案 |


---

## 7. 相关路径

| 角色 | 路径 |
|------|------|
| 设计 | `docs/costing/assembly-costing-design.md` |
| Router | `app/routers/costing/assembly_cost/{crud,calc}.py` |
| Repository | `app/repositories/costing/assembly_cost/` |
| Model | `app/models/costing/assembly_cost*.py` |
| DTO / VO | `app/schemas/dto/assembly_cost_dto.py`、`app/schemas/vo/assembly_cost_vo.py` |
| 月度核对导出 | `app/services/costing/monthly_bundle_export/` |
| 前端一览 / 计算 | `static/js/features/costing/assembly-cost/{list,calc}/` |
| 前端过程页 | `static/js/features/costing/assembly-cost/calc-report/boot.js` |
| 测试 | `tests/costing/test_assembly_cost_export.py`、`test_assembly_calc_report_export.py`、`test_monthly_bundle_export.py` |

测试 import 走真实模块：短码从 `codes`，焊费 ID 从 `export.workbook.builder`，列头从 `export.workbook.columns`，不要经 Service `__all__` 转发。
