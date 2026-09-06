# 采购签约报表 — 设计说明

> **状态：设计稿（未落地）。** 只读查询 + 导出，**不算价、不落结果表**。  
> 切片：**`costing`**（下游组合）。  
> 集合与供应商：[bom-procurement-objects-design.md](../bom/bom-procurement-objects-design.md)、[bom-procurement-object-supplier-design.md](../bom/bom-procurement-object-supplier-design.md)。  
> 金额：[assembly-costing-design.md](assembly-costing-design.md)（`should_cost`）。  
> 硬约束：[architecture.md](../architecture.md)。评审已否决第二套委外核价表（P16）；本文不是那张表。

---

## 0. 一句话

**按供应商出合同附件。** 行来自已指定对方的采购对象；列是查询窗口内每个自然月一列应成本。给采购和二级厂签合同用，不是总成一览的单月核价卡。

---

## 1. 为什么单独切片

| 现网 | 不够的地方 |
|------|------------|
| 采购对象列表 | 无月度金额 |
| 总成一览 · 采购视图 | **一个月**一张卡，不能按合同期横排 |
| 年度零件价 | 年协议价，不是应成本月序列 |

本切片 **禁止**：

- 再算一遍 walk / 间接 / 焊接。
- 再实现一套 `object_kind` 分类器。
- 新建 `costing_outsourced_*` 结果表。
- 回写采购对象或总成卡。

依赖方向：`costing` → 只读 `bom` 采购对象 + 只读 `costing_assembly_costs`。BOM 不得依赖本切片。

---

## 2. 查询范围

必填：

| 键 | 含义 |
|----|------|
| `location` | 采购基地 |
| `vehicle_model` | 项目 |
| `bom_version` | BOM 版本（解析当前 snapshot，与清单相同） |
| `start_year` + `start_month` | 窗口起（含） |
| `end_year` + `end_month` | 窗口止（含） |

可选：`supplier_name`（精确或规范化后全等，签约附件按一家一导）。

窗口规则：

- 闭区间，按自然月展开列。例：`2026-01`～`2026-03` → 三列；`2025-11`～`2026-02` → 四列。
- 开始不得晚于结束。
- **列数上限 12**（一次查询）。常用 **3～6** 个月；页面默认 3 个月（结束 = 开始 + 2 月）。
- 禁止固定 1～12 月全年横表当唯一形态。
- 超过 12 个月 → `BusinessException`（400），不要截断 silently。

清单未生成 → 404 或业务 400「请先生成采购对象清单」（与 summary 一致，实施时与现网采购对象 summary 对齐）。  
检测 `qa_passed=false`：**允许查、允许导出**，页头标明未通过（与清单导出相同：看见缺口，不假装合格）。

---

## 3. 行集

默认签约包（签合同用）：

```text
section = object
confirm_status = outsourced
supplier_name 非空
该 snapshot 的清单行
```

自制、待定、未指定供应商：**默认不出**。筛选项可打开「含未指定」供采购补洞，但导出文件名/页头须标明「含未指定」，避免当合同附件发出去。

核对区（标准件/胶等、异常）**永不进入**本报表。有子件的 L0 成品不在集合里，也不会出现。

同一 `part_number` 多行都保留，按 `source_node_id`（清单行 id）一行，**禁止按零件号去重**。

排序：供应商 → 供货总成零件号 → 本行零件号 → id。

---

## 4. 列与格子

固定列（抄清单行快照，现场读，不另存）：

| 列 | 来源 |
|----|------|
| 供应商 | `supplier_name` |
| 零件号 / 名称 | 清单行 |
| 对象种类 | `object_kind` → labels 中文 |
| 供货总成零件号 / 名称 | `l0_*` |
| 原件行号 | `excel_row`（核对，可选列） |

动态列：窗口内每个月一列，表头 `YYYY-MM` 或 `N月`（跨年必须带年，避免两个「1月」）。

格子金额：**只抄** `costing_assembly_costs.should_cost`，匹配：

```text
location + vehicle_model + bom_version
+ source_node_id = 清单行.source_node_id
+ year / month = 该列
```

`should_cost` 恒等于月总账 `total_amount`（不含 I1～I8）。合同读应成本，不读 `grand_total`。

某月无卡、卡 `failed`、或 `calc_status` 非成功：**格子空**（JSON `null`）。不拿邻月填，不在本切片补算。  
卡存在且金额为 0：写出 `0`（与空不同）。

一期 **不出** `vendor_quote` / 价差。报价仍在总成一览；本表专供应成本序列。

禁止把父卡与子卡金额加总。一行只对应该对象自己的卡。

---

## 5. 产品形态

侧栏 **核价** 下新页（不要塞进总成一览 Tab）：**采购签约报表**。仅查询 + 导出，无计算按钮、无审核。

对照：总成核价一览的 HUD 密表壳（`stamping-part-cost/list` 同族），强调色页内统一 `#FF1E27`。

筛选条：基地、项目、BOM 版本、开始年月、结束年月、供应商。供应商下拉 = 当前清单上已指定的去重名称（只读聚合，不是主数据）。

HUD：对象行数、已指定供应商数、窗口月数、缺月格子数（空格计数，提示哪些月还没算总成）。

分页：`page` + `size`，`page-size.js`。动态列随窗口变，表 `min-width` 随列数增加。操作列：无行内业务操作（不是确认页）；需要时只保留「详情」链到采购对象或总成卡（可选，一期可没有）。

禁止整行点击。禁止勾选列。

导出 Excel：与列表同一套筛选，**不分页**。一家供应商筛出来即一份附件。表头含范围与窗口；`qa_passed=false` 或含未指定须印在标题区。金额 VO 规则：Decimal JSON/Excel 用字符串固定小数位，禁止 `float`。

---

## 6. API / 分层 / 权限

```text
Router  → Costing 本切片 Service
              ├── 只读 ProcurementObjectRepository（行 + 清单头）
              └── 只读 AssemblyCostRepository（按节点 + 年月批量）
```

禁止 Router 查库；禁止 `prepare/engine/persist`；禁止异步任务。

建议路径（实施时再进 `Perm` / `permission-design.md`）：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/costing/procurement-contract-report` | 分页；Query 含范围与窗口；`page`+`size` |
| GET | `/api/costing/procurement-contract-report/export` | 同筛，Excel |
| GET | `/api/costing/procurement-contract-report/prep` | 可选：当前清单供应商去重、窗口校验、缺月统计 |

响应：`ApiResponse[PageResult[RowVO]]`。`RowVO` 含固定字段 + `month_amounts: list[MonthAmountVO]`（`year`/`month`/`should_cost`），**不要**把 1～12 写成固定 12 个字段。前端按窗口渲染列。

`PageResult.filters` 可用具名 VO：窗口起止、列清单、`qa_passed`。禁止签名 `dict[str, Any]`。

权限（落地时写入 catalog，本期文档先定名）：

| 码 | 用途 |
|----|------|
| `menu:procurement-contract-report` | 侧栏与路由 |
| `op:procurement-contract-report:view` | 查询 |
| `op:procurement-contract-report:export` | 导出 |

建议挂在核价分组下，与总成核价并列，不要复用 `menu:assembly-cost`。

目录（落地时）：

```text
app/services/costing/procurement_contract_report/
app/routers/costing/procurement_contract_report.py
app/schemas/dto|vo/procurement_contract_report_*.py
static/js/features/costing/procurement-contract-report/
```

无本切片 Model / 无 Parser。金额 join 走现网 `AssemblyCostRepository` 扩展只读方法，不要在 Service 里 `db.query`。

---

## 7. 缺数怎么展示

| 情况 | 行为 |
|------|------|
| 无采购对象清单 | 拒绝查询，指向生成页 |
| 有清单但无外发已指定行 | 空表，说明文案 |
| 窗口内部分月未算总成 | 行仍出，缺月空格；HUD 计缺月 |
| 总成已算但该对象无卡（清单后未重算） | 该行整段窗口可能全空；提示「请按当前清单重算总成」 |
| BOM 重导 `source_node_id` 失效 | 与总成 P18 相同：必须重生成清单并重算；本报表不猜旧 id |

---

## 8. 做 / 不做

| 做 | 不做 |
|----|------|
| 起止年月动态列（常用 3～6，上限 12） | 固定全年 12 列当唯一 UI |
| 格子只抄 `should_cost` | 本切片计算、落结果表、第二套引擎 |
| 默认外发且已指定供应商 | 标准件/胶等进合同包 |
| 按供应商筛 + 导出 | 合同状态机、电子签、一件多家 |
| 空格 = 该月无成功卡 | 用邻月或年度价填空 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-02 | 初稿：costing 只读签约横表；窗口起止月；行=采购对象；格=应成本。 |
