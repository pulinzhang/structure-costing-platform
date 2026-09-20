# 冲压检具费档案

> **状态：已落地（仅档案维护）。**  
> 关联：[冲压件模具管理](stamping-die-management-design.md)（布点几何，不读 AD+ 检具款）。  
> 硬约束：分层与切片见 [architecture.md](../architecture.md)。

---

## 0. 一句话

按 **采购基地 + 项目 + 零件号** 维护检具费（万元）与项目分摊数量（万台）。这是核价档案：零件价按号 lookup（元/件 = 万元÷万台）；**不写 L0 I7**（I7 仍是成品间接费，不是本件检具费）；本期不做单独的年度检具分摊台账。

筛选项与模具布点相同：来自 `stamping_parts` 级联（基地 → 项目），无版本、无冲压厂。模板零件来自 **模具布点** `stamping_die_parts`；没有模具布点则无需维护检具费。

---

## 1. 范围

| 做 | 不做 |
|---|---|
| Excel 模板带出工艺零件 + 同步整包覆盖上传 | 行内新增、审核流 |
| 列表单条编辑（检具费 / 分摊 / 状态）与单条删除 | 改基地、项目、零件号 |
| 唯一键 `location` + `vehicle_model` + `part_number` | 写入 `stamping_die_parts` / 模具单价表 |
| 状态 `effective` / `invalid` | 异步 worker、进度轮询 |
| 默认检具费 **0.8** 万、分摊 **10** 万台 | 年度分摊台账、`gauge_alloc_fee`、写 L0 I7 |

须该基地+项目已有模具布点。零件号必须在该范围 `stamping_die_parts` 中，否则整单拒绝并列缺失号。无模具的零件不进模板、也不算检具费。

唯一约束在库中兜底；Service 先按范围删后写。冲突中文 **409**，不把 UNIQUE 原文甩给用户。

---

## 2. 字段

表 `stamping_gauge_fees`。

| 字段 | 说明 |
|------|------|
| `location` | 采购基地 |
| `vehicle_model` | 项目（`normalize_vehicle_model`） |
| `part_number` | 规范化零件号；入库用模具布点号码 |
| `part_name` | 展示用；上传以模具布点名称为准（Excel 名称仅人读） |
| `gauge_fee` | `Decimal`，万元，默认 0.8 |
| `allocation_qty` | 万台，正整数，默认 10 |
| `status` | `effective` 生效 / `invalid` 失效 |

---

## 3. 接口

前缀 `/api/stamping/gauge-fees`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/filters` | 工艺级联（上传 view 或列表 view 任一） |
| GET | `/template?location=&vehicle_model=` | 必须已选基地+项目；每行一个模具布点零件，预填 0.8 / 10 / 生效；无布点则拒绝 |
| POST | `/upload` | Form：`location`、`vehicle_model`、`file`；该范围整包覆盖；登记 `file_category=stamping_gauge_fee` |
| GET | `/` | 分页 `page`+`size`；筛 location / vehicle_model / part_number / status；`filters.summary` 为 HUD（检具费合计 / 条数，与列表同一套筛选） |
| GET | `/export` | 与列表相同筛选，不分页；Excel 每行含基地、项目、零件号、名称、检具费、分摊、状态 |
| PUT | `/{id}` | 改检具费、分摊数量、状态；不改基地/项目/零件号 |
| DELETE | `/{id}` | 单条删除 |
| DELETE | `/scope` | 按基地+项目整包删除 |

模板列：零件号、零件名称、检具费（万元）、项目分摊数量（万台）、状态。检具费与分摊数量**必填**，空单元格或负数整单拒绝（模板仍预填 0.8 / 10）。

页面：`#/stamping-gauge-fee-upload`、`#/stamping-gauge-fee`。权限：`menu:stamping-gauge-fee-group`；上传 `view`/`upload`；列表 `view`/`update`/`delete`/`export`。

---

## 4. 分层

- Router：`app/routers/stamping/gauge_fee.py`
- Service：`app/services/stamping/gauge_fee/`（列表 / 上传 / 模板 / 导出；工程变更抄写/回滚删除）
- Parser：`app/parsers/stamping/gauge_fee_parser.py`
- Repo：`app/repositories/stamping/gauge_fee/repository.py`
- 模具零件：只读 `StampingDiePartRepository.list_parts_for_scope`（无模具则无需检具费）

---

## 5. 工程变更

改图换号时，若旧号有 `effective` 档，工程变更管线调本切片 Service **抄到新号**；回滚调本切片 **按 id 删新行**。旧号行不动。实现在 `gauge_fee/engineering/change.py`（Service 只转发）。本切片 **不** import `engineering_change`。规则见 [part-number-revision-design.md](../engineering-change/part-number-revision-design.md) §4.3.1。
