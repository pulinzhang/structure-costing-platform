# 采购对象清单 — 设计说明

> **状态：已落地。** 口径与代码以本切片为准；对人展示文案见 `labels.py` / `labels.js`。  
> 切片：**`bom`**。生成时只读 `bom_snapshots` / `bom_nodes`，写入本切片采购对象表与生成日志。  
> 样本：`excel_sample/T13J项目车身件材料清单 (1).xlsx`（T13J · D/09）。  
> 硬约束：分层与切片见 [architecture.md](../architecture.md)。

**对人展示 vs 内部码。** 页面、生成摘要、Excel 单元格用中文（退化供货件、分总成、冲压件、标准件/胶等）。库字段、API、分类函数仍用 `l0_degenerate` / `other_leaf` 等码。Excel **工作表名**不能含 `/`，标准件分区表名用「标准件及胶等」。

---

## 0. 一句话

**清单定集合。** 一版材料清单对应一份 **采购对象清单**：按树结构列入退化供货件、分总成、冲压件，检测后落库，供采购核对并确认外发/自制。

「生成」是动作（从树上把该列入的节点写成清单）。本文回答 **谁是采购对象**。不管价、不管合同怎么签。

---

## 1. 业务是什么

交主机厂的是 **供货总成（有子件的 L0）**。采购要管的不是这层容器，而是能单独向二级买的件，以及「成品就是一张板」的退化供货件。

| 列入采购对象 | 树上的样子 | 对人展示 |
|--------------|------------|----------|
| 退化供货件 | L0，下面没有 L1 | 退化供货件 |
| 分总成 | L1，下面有 L2 | 分总成 |
| 冲压件 | L1，下面没有孩子，且是板料 | 冲压件 |

有子件的 L0 **不列入**。L2 跟在分总成下，**不单独列入**。L1 上的螺母、胶等不是采购对象，进 **核对区（标准件/胶等）**，防止把板料漏判成外购。

主机厂不允许把有子件的 L0 整层外发：**有子件的 L0 永不列入采购对象**。备注写了「凸焊总成供货」也不列入，只进 **核对区（异常）**。

---

## 2. 分类规则（列入只靠结构）

子节点 = 同 snapshot 下至少一行 `parent_id = 本节点.id`。

| `object_kind` | 条件 | 对人展示 |
|---------------|------|----------|
| `l0_degenerate` | `level=0` 且无子节点 | 退化供货件 |
| `l1_subassembly` | `level=1` 且有子节点 | 分总成 |
| `l1_stamping` | `level=1` 且无子节点，且是板料冲压件（§3） | 冲压件 |

| 不列入采购对象 | 落库 `section` | 对人展示 |
|----------------|----------------|----------|
| `level=0` 且有子节点 | 默认不落行；备注含委外话术 → `anomaly` | 异常 |
| `level=2` | 不落行；件数写进清单头对账 | — |
| L1 无子件、但不是冲压件 | `other_leaf` | 标准件/胶等 |

列入 **禁止** 看：焊接原文有无、备注关键词、年度零件价有无行。这些最多当行字段或告警。

---

## 3. L1 无子件：冲压件还是标准件/胶等

分总成用「有子件」即可，不必猜名称。  
L1 叶子必须把 **板料** 和 **标准件 / 胶 / 塑料** 分开，否则会把螺母当成采购对象里的冲压件。

认 `l1_stamping`（顺序，命中即停）：

1. `node_role = make`
2. `thickness_mm` 非空
3. 现网 `resolve_manufacturing_category(...) == "stamping"`

其余 L1 叶子 → `section=other_leaf`。T13J 叶子焊接原文为 0，**不能**用焊信当冲压件条件。

---

## 4. 退化供货件：全部列入，再标亚类

无子件的 L0 **全部** `section=object` 且 `object_kind=l0_degenerate`。亚类只读，不改变是否列入：

| `degenerate_subtype` | 对人展示 | 规则（看原文，不编工艺） | T13J |
|----------------------|----------|--------------------------|------|
| `special_process` | 特殊工艺 | `weld_info` 或 `remark` 含电泳 / 面积 / 黑漆 / 喷粉 / 电镀 | 6 |
| `stamping_blank` | 冲压毛坯 | 其余 | 8 |

无工艺 ≠ 电泳，也 ≠ 不列入。外发还是自制，用行上的 `confirm_status`。

---

## 5. 行上带出的字段（展示，不参与列入）

生成时从节点 **抄一份快照** 落到行上。树仍是分类真相；再生成按当时的树重算。

| 列 | 来源 |
|----|------|
| `weld_info` / `remark` | 节点原文 |
| `has_outsource_remark` | 备注含约定词则为真（提示，不是开关） |
| `material` / `thickness_text` / `material_mill` | 材料列；厂家是钢厂/紧固件商/胶商，**不是**二级冲焊厂 |
| `parent_part_number` / `parent_part_name` | 直接父件（L1 即供货总成；退化供货件为空） |
| `l0_part_number` / `l0_part_name` | **核对凭据**：所属供货总成零件号/名称。L1 沿父上溯到 L0；退化供货件、异常 L0 **填自身**。列表、导出必带，不要让人只对着本行零件号对材料清单 |
| `excel_filename` / `excel_row` | **核对凭据**：导入时的 **原始 Excel 文件名**、**Excel 界面行号**（1-based，与打开原件看到的行号一致）。从 `bom_nodes` 抄，列表/导出必带 |
| `excel_sheet_name` | 来源工作表名（节点有则抄）。多表时和行号一起对原件 |
| `child_count` | 直接子节点数 |
| `source_node_id` | `bom_nodes.id`；同一零件号可出现在多棵树上 |
| `data_gap` | 可空。退化供货件材料/料厚/厂家全空 → `l0_material_missing` |
| `alert_code` | 可空。§7.4 告警码，不否决列入 |

约定词（仅打标，可按项目补）：`凸焊总成供货`、`总成供货`、`冲压单件供货`、`单件供货`、`黑漆件供货`、`电泳`。

本文不解析、不猜测二级供应商名称。行上 **禁止** 存单价、一口价、供应商名。

---

## 6. T13J 金标准

解析口径与现网 `node_parser` 一致：A 列非数字即停。

| 树上 | 件数 | 采购对象清单 |
|------|------|----------------|
| L0 | 44 | — |
| L0 有子件 | 30 | **不进 `object`** |
| L0 无子件 | **14** | 全部 `l0_degenerate` |
| L1 | 205 | — |
| L1 有子件 | **53** | 全部 `l1_subassembly` |
| L1 无子件 | 152 | `l1_stamping` + `other_leaf` |
| L2 | 108 | 不落行；须等于 53 个分总成的孩子合计 |

`other_leaf` **允许非零**。`l1_stamping` 实数用 §3 跑出来，写入清单头计数。

退化供货件亚类金标准：

| 亚类 | 件数 | 零件号 |
|------|------|--------|
| `special_process` | 6 | `501012176AA`、`554003393AA`、`403014115AA`、`403014116AA`、`T15-3301097`、`T15-3301098` |
| `stamping_blank` | 8 | 含顶横梁Ⅱ `502008112AA` 等 |

焊信一致性（告警，不改分类）：53 个分总成全部有焊接原文；L1 叶子焊接原文为 0。

---

## 7. 检测：怎样才叫清单对了

对 **一个 snapshot** 必须同时满足。7.1–7.3 决定清单头 `qa_passed`。失败仍落库（检测要看见哪漏了）。`qa_passed=false` 时 **禁止确认、禁止审核**；导出仍允许（标明未通过）。

### 7.1 完备

```text
|{level=0 且无子件}|  == |object_kind=l0_degenerate|
|{level=1 且有子件}|  == |object_kind=l1_subassembly|
|{level=1 且无子件}|  == |l1_stamping| + |other_leaf|
```

第三条是叶子分完，不是「152 必须全是冲压件」。

### 7.2 互斥

同一 `source_node_id` 只出现在一行。  
有子件的 L0、全部 L2：`section=object` **零行**。

### 7.3 结构对账

| 检查 | 合格 |
|------|------|
| `l1_subassembly` 的 `child_count ≥ 1`，孩子全是 L2 | 是 |
| `l1_stamping` / `l0_degenerate` 的 `child_count = 0` | 是 |
| 每个 `section=object` 的 L1，父节点是有子件的 L0 | 是 |
| 分总成孩子合计 = 该 snapshot 全部 L2 | 是（T13J：108） |
| 每一行 `l0_part_number` 非空（退化供货件 / 异常 L0 为自身） | 是 |
| 每一行能从节点抄到 `excel_filename` 与 `excel_row` | 是（抄不到则告警，不挡列入） |

### 7.4 告警（不否决 `qa_passed`）

| `alert_code` | 含义 |
|--------------|------|
| `l0_outsource_remark` | 有子件的 L0 备注含「凸焊总成供货」等；**仍不列入采购对象** |
| `subassembly_no_weld` | `l1_subassembly` 且 `weld_info` 空（T13J 不应有） |
| `stamping_has_weld` | `l1_stamping` 且 `weld_info` 非空（T13J 不应有） |
| `l0_material_missing` | 退化供货件材料/料厚/厂家全空（现网解析常如此） |
| `other_leaf_looks_stamping` | `other_leaf` 名称像支架/加强板且有料厚 |
| `excel_trace_missing` | 节点上原始文件名或行号为空，对原件核对不便 |

修 `node_parser`、让退化供货件落到自身材料，是 **解析** 问题，不是改列入规则。修好后再生成，`l0_material_missing` 应变少。

---

## 8. 表（按业务命名）

这是 **一版材料清单的采购对象台账**，不是临时计算结果。页面和导出只读本切片结果表，**禁止**每次打开列表再扫 `bom_nodes` 当结果。

### 8.1 三张表

```text
bom_procurement_object_lists          清单头：一版 BOM 一份采购对象清单
 └── bom_procurement_objects          清单行：采购对象 / 标准件/胶等 / 异常
bom_procurement_object_generate_logs  一次「开始生成」一条终态日志（同步，无 processing）
```

| 表 | 业务 |
|----|------|
| `bom_procurement_object_lists` | 这份材料清单的采购对象清单一份（含检测结论、结构计数） |
| `bom_procurement_objects` | 清单里的每一行：要采购核对的对象，或核对用的标准件/胶等、异常 |
| `bom_procurement_object_generate_logs` | 生成历史：范围、计数、检测、过程全文 |

归属 **`bom` 切片**。头表 `snapshot_id` 外键 → `bom_snapshots.id`，`ON DELETE CASCADE`。  
现网覆盖导入会 **删旧 snapshot 再建**：清单随材料清单一起没，必须对新 snapshot **再生成**。一期 **不** 把确认迁到新 snapshot（`source_node_id` 已变，对错行的风险大于省勾选）。

### 8.2 清单头 `bom_procurement_object_lists`

一 snapshot 至多一份清单。唯一键：`snapshot_id`。

| 字段 | 业务含义 |
|------|----------|
| `snapshot_id` | 哪一版材料清单 |
| `location` / `vehicle_model` / `bom_version` | 从 snapshot 冗余，列表筛选不必总 join |
| `source_filename` | 该版材料清单导入时的 **原始 Excel 文件名**（`bom_snapshots.source_filename`），页头核对用 |
| `qa_passed` | 7.1–7.3 全过：这份清单可以给采购用 |
| `qa_error_text` | 未通过时的人读原因；通过可空 |
| 结构计数 | `l0_count`、`l0_with_children_count`、`l2_count`、`subassembly_child_sum` |
| 采购对象计数 | `object_l0_degenerate_count`、`object_l1_subassembly_count`、`object_l1_stamping_count` |
| 核对区计数 | `other_leaf_count`、`anomaly_count` |
| `generated_at` / `generated_by` | 最近一次生成 |

`AuditUserMixin` 照现网其它 BOM 结果表。

### 8.3 清单行 `bom_procurement_objects`

一行 = 树上一个节点在本份清单里的角色。

| 字段 | 业务含义 |
|------|----------|
| `list_id` | 所属采购对象清单，级联删 |
| `section` | `object` 采购对象；`other_leaf` 标准件/胶等（核对）；`anomaly` 异常（核对） |
| `object_kind` | 仅 `section=object`：`l0_degenerate` / `l1_subassembly` / `l1_stamping`；其余空 |
| `degenerate_subtype` | 仅退化供货件：`special_process` / `stamping_blank` |
| `source_node_id` | 生成时的 `bom_nodes.id` |
| `part_number` / `part_name` / `level` / `node_role` | 本行零件快照 |
| `qty` / `qty_unit` | 相对父件；`qty` 用 `Numeric` / `Decimal` |
| `l0_part_number` / `l0_part_name` | **核对凭据**。所属供货总成（材料清单总成列）。L1 / 标准件/胶等：上溯到 `level=0`；退化供货件、异常（有子件的 L0）：填本行。必填，禁止空 |
| `parent_part_number` / `parent_part_name` | 直接父件。L1 与 `l0_*` 相同；退化供货件为空。结构用，**不够当核对列**（退化供货件没有父件） |
| `excel_filename` | **核对凭据**。该行在原件中的文件名，从节点 `excel_filename` 抄（与清单头 `source_filename` 通常相同，行上自带以免导出后对不上） |
| `excel_sheet_name` | 工作表名，节点有则抄 |
| `excel_row` | **核对凭据**。Excel **界面行号**（1-based，与打开原件左侧行号一致），从节点 `excel_row` 抄。不是库内 id、不是 sort_no |
| `child_count` | |
| `weld_info` / `remark` / `has_outsource_remark` | 原文与经营话术提示 |
| `material` / `thickness_text` / `material_mill` | 牌号/料厚/钢厂等，不是二级厂名 |
| `data_gap` / `alert_code` | 可空 |
| `confirm_status` | 仅采购对象：`pending` 待定 / `outsourced` 外发 / `in_house` 自制。核对区行固定 `pending` 且 API 禁止改 |
| `confirmed_by` / `confirmed_at` / `confirm_remark` | 最近一次确认（外发/自制） |
| 审核 | 仅 `section=object`。`audit_status`：`pending` 待审 / `approved` 已审。字段同焊接单价：`audited_by` / `audited_at` / `audit_remark`，`reverse_audited_by` / `reverse_audited_at` / `reverse_audit_remark`。核对区不审核 |

唯一键：`(list_id, source_node_id)`。同一节点不能既是采购对象又是标准件/胶等。

### 8.4 生成（覆盖写）

入口：选定 **基地 + 车型 + BOM 版本**（服务层解析当前 `snapshot`），点 **生成**（对齐焊接工艺拆解，不是上传 Excel）。口语里可以说「把采购对象从树上生成出来」，界面和表名不要写「抽取」。

1. 读该 snapshot 全部 `bom_nodes`，纯函数分类 + 检测。  
2. **一个事务**：删该 snapshot 旧清单头（级联删行）→ 写新头 + 新行。  
3. 同一 snapshot 再生成：按 `source_node_id` **带回** 旧行的确认三态 / 确认人时 / 备注。新出现的节点 `pending`；已不在树的确认丢弃。  
4. 覆盖导入换了 snapshot：旧清单已随旧 snapshot 删掉，新生成全是 `pending`。  
5. 写一条 `bom_procurement_object_generate_logs`（成功或失败终态）。

检测未通过：照样提交，`qa_passed=false`。不要为了「名单好看」只写一半采购对象。

**已审核锁定：** 该 snapshot 下只要有一行 `audit_status=approved`，禁止再生成覆盖（`BusinessException` `code=409`）。须先 **批量反审核**。不要把已审行悄悄跳过再抽一半。

一期 BOM 节点量级 **同步生成**（无异步任务、无 processing 锁）。生成页有进度条是前端等待 HTTP，不是后台 worker。

### 8.5 确认、审核、CRUD

对齐现网 **年度零件价 / 焊接单价** 列表：删除、审核、反审核 **只走批量、按范围、意见必填**。禁止单条审核/反审核/删除 API，禁止操作列做这三件事。

**确认（业务勾选，不是审核）**

- 只改 `section=object` 的 `confirm_status`（待定 / 外发 / 自制）和确认备注。
- 不改 `object_kind`、核对凭据、材料快照。
- `qa_passed=false` 或 `approved` 时拒绝（已审须先批量反审核）。
- 确认允许 **单条**（操作列改外发/自制）：这是「这一件怎么买」，不是锁定。

**删除 / 审核 / 反审核（只批量，按清单范围）**

与年度零件价「按基地 + 年」相同：body 带 **范围键**，不传行 id、不按勾选。

| 项 | 口径 |
|----|------|
| 范围 | 一份清单 = 基地 + 车型 + BOM 版本（对应一个 snapshot）。只处理该清单下 `section=object` |
| 入口 | 列表工具栏按钮 + 抽屉；**审核意见 / 反审核原因必填**（`min_length=1`） |
| 删除 | 只删 `pending`；`approved` **跳过**，返回 `skipped_approved_count` |
| 审核 | 把范围内 `pending` 改为 `approved`；已审跳过；意见写入 `audit_remark` |
| 反审核 | 把范围内 `approved` 改回 `pending`；非已审跳过；原因写入 `reverse_audit_remark` |
| 锁定 | `approved` 禁止改确认、禁止再生成覆盖 |
| 检测 | `qa_passed=false` 时拒绝审核（可导出、可删 pending 以便重生成） |

不要求先确认外发才能审。列表要能筛未确认已审。

删行后重算清单头计数；完备性被破坏则 `qa_passed=false`。核对区不参与这三套批量（不是采购对象）。

**CRUD**

| 字母 | 做什么 | 不做什么 |
|------|--------|----------|
| C | **生成** 整份清单 | 手填一行乱入分类 |
| R | 列表分页、summary、单条详情、生成历史 | |
| U | 单条改确认（待审） | 改总成号、Excel 行号、分类；单条审核 |
| D | **仅批量删除**（按范围，跳过已审） | `DELETE /items/{id}`；操作列删除 |

**导出 Excel**

- 与列表同一套筛选，不分页。
- 三张工作表（采购对象 / 标准件及胶等 / 异常），无封面。必含原件文件名、行号、供货总成、本行零件、对象种类、确认、审核。
- 冻结 `G6`；打印标题 `A:F`。相邻行相同供货总成零件号+名称时合并 E/F。
- 色板与冲压模具费导出同族（靛蓝标题 / 石板分组 / 品牌红判定）。
- 无「关注点」列。
- `qa_passed=false` **仍允许导出**（标明未通过）。

### 8.6 分层

```text
Router  → Service 门面 → generate / audit / generate_log / export
              └── classify 纯函数；只读 BomNodeRepository / BomSnapshotRepository
```

禁止 Router 写 SQL；禁止生成时读年度价、焊接拆解、冲压价。  
Parser 不参与（树已在 `bom_nodes`）。

路径：

```text
app/models/bom/procurement_object.py
app/models/bom/procurement_object_generate_log.py
app/repositories/bom/procurement_object_repository.py
app/services/bom/procurement_object/   labels · classify · generate · audit · export · mapping · service
app/routers/bom/procurement_object.py
app/schemas/dto|vo/bom_procurement_object_*.py
static/js/features/bom/procurement-object/
```

对人展示文案（勿在页面/导出再写一套）：

- `app/services/bom/procurement_object/labels.py`
- `static/js/features/bom/procurement-object/labels.js`

API 前缀：`/api/bom/procurement-objects`。生成与批量范围键均为 **基地 + 车型 + BOM 版本**（不是客户端传 `snapshot_id`）。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/generate/prep-stats` | 生成页 KPI：节点 / 将列入 / 标准件/胶等 / 异常 / 已审锁定 |
| POST | `/generate` | body：范围；有已审行则 409 |
| GET | `/generate/logs` | 生成历史分页 `page`+`size` |
| GET | `/generate/logs/{log_id}` | 过程全文 |
| GET | `/summary` | 当前范围的清单头（尚未生成则 404） |
| GET | `/` | 分页 `page`+`size`；筛范围 / section / object_kind / confirm_status / audit_status / part_number / l0_part_number / excel_row；`section` 空 = 全部 |
| GET | `/items/{id}` | 单条详情 |
| PATCH | `/items/{id}/confirm` | 单条确认三态（待审） |
| POST | `/batch-approve` | **按范围** 批量审核；`audit_remark` 必填；禁止 ids |
| POST | `/batch-reverse-audit` | **按范围** 批量反审核；`reverse_audit_remark` 必填；禁止 ids |
| POST | `/batch-delete` | **按范围** 批量删除 pending；跳过已审；禁止 ids |
| GET | `/export` | 与列表相同筛选，不分页，Excel |

禁止：`POST /items/{id}/approve`、`POST /items/{id}/reverse-audit`、`DELETE /items/{id}`、按勾选 id 的 batch。

---

## 9. 产品：生成 / 列表 / 审核 / 导出

侧栏（焊接工程下）：**采购对象** — **两个界面**：生成页 + 列表页。

### 9.1 前端风格

两页视觉与交互壳对齐 `static/js/features/costing/stamping-part-cost/`，不要对齐年度零件价的浅阶面板，也不要自创第三套。

| 页 | 对照 | 抄什么 |
|----|------|--------|
| 生成 | `stamping-part-cost/calc/template.js` | 顶栏标题；筛选条；筛选下 KPI；主按钮「开始生成」；进度面板 |
| 列表 | `stamping-part-cost/list/template.js` | HUD 外框；看板 + 批量按钮；胶囊筛选；密表；`page-size.js`；抽屉 z-index ≥ 80/85 |

强调色页内统一 **`#FF1E27`**，不要和 `#d32f2f` 混用。  
HUD：**采购对象**是霓虹强调格；标准件/胶等、待审、已审为普通计数。检测未通过用警告文案，**不要**照抄「本期均价」。  
操作列只 **确认**（及详情）；禁止整行点击；**无勾选列**。批量审核/反审核/删除的规则仍是 §8.5。

禁止另起 `style.css` 业务 class。

### 9.2 页面内容

列表页签：**全部**（默认，不传 `section`）| 采购对象 | 标准件/胶等 | 异常。HUD 展示采购对象条数、标准件/胶等、待审、已审。`qa_passed=false` 用错误文案，不要静默当成功。

工具栏：**批量审核 / 批量反审核 / 批量删除** + 导出 Excel。抽屉展示当前清单范围（基地 · 车型 · 版本），意见必填。删除跳过已审。禁止勾选行再批量。

**核对列：** 列表与导出须能直接对回原件：

1. **原件**：`excel_filename`（页头再用清单的 `source_filename`）
2. **行号**：`excel_row`（Excel 界面 1-based）
3. **供货总成**：`l0_part_number` / `l0_part_name`
4. **本行**：零件号 / 名称
5. **对象种类 / 确认 / 审核**

列表 **无「关注点」列**。不要让采购只拿本行零件号去材料清单里搜。工作表名有则一并展示。

导出与 §8.5 相同。同一 `part_number` 多行都导出。不提供「Excel 勾完再导回确认/审核」；确认和审核只在系统里做。

权限（已进 `catalog.json`）：

| 码 | 用途 |
|----|------|
| `menu:bom-procurement-object-group` | 侧栏分组 |
| `menu:bom-procurement-object` | 生成页 |
| `op:bom-procurement-object:generate` | 生成 |
| `menu:bom-procurement-object-list` | 列表页 |
| `op:bom-procurement-object-list:view` | 查询 |
| `op:bom-procurement-object-list:update` | 单条确认 |
| `op:bom-procurement-object-list:delete` | 批量删除 |
| `op:bom-procurement-object-list:approve` | 批量审核 |
| `op:bom-procurement-object-list:reverse` | 批量反审核 |
| `op:bom-procurement-object-list:export` | 导出 Excel |

---

## 10. 和现网 BOM 的边界

| 模块 | 关系 |
|------|------|
| `bom_nodes` | 分类时只读；对外以采购对象清单为准 |
| 覆盖导入 | 删 snapshot → 级联删清单 |
| `node_parser` | 生成不改解析；材料落不到退化供货件时打 `data_gap` |
| `manufacturing_category` | L1 叶子是否冲压件，复用，不新开词典 |
| 焊接工艺拆解 | **不读** |
| 年度零件价 | **不读** |

---

## 11. 做 / 不做

| 做 | 不做 |
|----|------|
| 按树列入三类采购对象并落库 | 用备注 / 焊信 / 年度价决定列不列入 |
| 清单头记检测结果；失败也落库 | `qa_passed=false` 仍当「名单已合格」 |
| 标准件/胶等 + 异常进核对区 | 把有子件的 L0、L2 写入采购对象 |
| 同 snapshot 再生成带回确认；已审禁止覆盖 | 覆盖导入后自动把确认对到新 `source_node_id` |
| 确认外发/自制（单条）；批量审核/反审核/删除（按清单） | 单条审核、单条删除、按 id 勾选批量；手建一行改分类；Excel 导回当审核 |
| 生成页/列表页抄零件价格计算 + 一览 | 抄年度零件价列表壳；自创第三套样式 |
| 已审禁止改确认/删除/再生成 | 算单价、应成本 |
| 退化供货件全部列入，再标亚类 | 无工艺就不列入，或编成电泳 |
| 同一零件号多行都保留 | 按零件号去重 |
| 对人展示走 `labels` | 页面再写「其它叶子」「退化 L0」当产品文案 |

---

## 12. 相关代码与文档（本切片）

| 位置 | 角色 |
|------|------|
| `app/models/bom/node.py` | `level` / `parent_id` / `node_role` / `weld_info` / `remark` / `excel_row` |
| `app/parsers/bom/node_parser.py` | 树怎么进库；L0 材料是否落地 |
| `app/common/bom/manufacturing_category.py` | L1 叶子是否 `stamping` |
| `app/services/bom/welding_process_breakdown/bom_tree.py` | 树上备注仍写「退化 L0」，分类条件与它对齐 |
| `app/services/bom/bom_upload_service.py` | 覆盖导入删 snapshot，清单须级联没 |
| [bom-annual-part-prices-design.md](bom-annual-part-prices-design.md) | 价表；本文不读 |
| [outsourced-assembly-costing-design.md](../costing/outsourced-assembly-costing-design.md) | 下游应成本；集合以本清单为准 |
| `static/js/features/costing/stamping-part-cost/calc/` | 生成页 UI 对照 |
| `static/js/features/costing/stamping-part-cost/list/` | 列表页 UI 对照 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-31 | 初稿：三类对象、检测、导出。 |
| 2026-08-31 | 收成上游文档：只认 BOM 结构与确认。 |
| 2026-08-31 | 落库：清单头/行、生成覆盖、同 snapshot 带回确认。 |
| 2026-08-31 | 文案与表名改为采购对象清单；动作称生成，不再用抽取当业务名。 |
| 2026-08-31 | 行上增加供货总成 `l0_part_number` / `l0_part_name` 作核对凭据；列表筛选与导出必带。 |
| 2026-08-31 | 核对凭据补原始 Excel 文件名与界面行号（清单头 `source_filename`，行上 `excel_filename` / `excel_row`）。 |
| 2026-08-31 | 列表对齐现网：确认、审核/反审核、批量、导出 Excel、按树生成的 CRUD；已审锁定。 |
| 2026-08-31 | 删除/审核/反审核改为只批量、按 snapshot 范围、意见必填；禁止单条与按 id。 |
| 2026-08-31 | 生成页/列表页前端必须对齐 `stamping-part-cost` 计算页与一览（HUD / 筛选条 / 密表）。 |
| 2026-08-31 | 改为已落地：对人展示与内部码分开；补生成日志 / prep-stats；导出三表与列表页签、HUD 与现网一致。 |
