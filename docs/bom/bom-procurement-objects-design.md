# 采购对象清单 — 设计说明

> **状态：分类 / 生成 / 确认 / 审核已落地。** 口径与代码以本切片为准；对人展示文案见 `labels.py` / `labels.js`。  
> **未落地：** §14 跟树根有效期（as_of 列/数/检/审）、设变增量插行。生成页拒绝整包是 **合册落地时** 才改的门禁，落地前仍 §8.4。  
> **主数据对齐（未做完）：** 基地筛已接 `LocationService`；生成查找 snapshot、项目筛、代号大写见 §13。指定合同对方见独立设计。  
> 切片：**`bom`**。生成时只读 `bom_snapshots` / `bom_nodes`，写入本切片采购对象表与生成日志。  
> 界面：**项目**。库字段：`vehicle_model`。  
> 基地：[location-design.md](../masterdata/location-design.md)。项目：[vehicle-model-design.md](../masterdata/vehicle-model-design.md)。  
> 样本：`excel_sample/T13J项目车身件材料清单 (1).xlsx`（T13J · D/09）。  
> 树根有效期现网改造见 [bom-process-die-effective-period-design.md](../engineering-change/bom-process-die-effective-period-design.md)。对象行不写生失效；**列表 / 检测 / 审核 / 核价**严格跟所属树根 as_of。设变增量带出见 §14、[工程变更](../engineering-change/part-number-revision-design.md) §4.4。  
> 硬约束：分层与切片见 [architecture.md](../architecture.md)；引用保护见宪法 **§4.3**。

**对人展示 vs 内部码。** 页面、生成摘要、Excel 单元格用中文（退化供货件、分总成、冲压件、标准件/胶等）。库字段、API、分类函数仍用 `l0_degenerate` / `other_leaf` 等码。Excel **工作表名**不能含 `/`，标准件分区表名用「标准件及胶等」。

---

## 0. 一句话

**清单定集合。** 一版材料清单对应一份 **采购对象清单**：按树结构列入退化供货件、分总成、冲压件，检测后落库，供采购核对并确认外发/自制。

「生成」是动作（从树上把该列入的节点写成清单）。本文回答 **谁是采购对象**。指定合同对方见 [bom-procurement-object-supplier-design.md](bom-procurement-object-supplier-design.md)；按月应成本签合同见 [procurement-contract-report-design.md](../costing/procurement-contract-report-design.md)。列入规则仍不管价。

```
基地 ★
  └── 项目
        └── bom_snapshots     ← 项目直接下一跳（复合 FK）
              └── 本文清单头   ← 挂 snapshot CASCADE；不是项目下一跳
                    └── 清单行
```

生成不是传 BOM，也不立项。没有材料清单：停止，去焊接工程上传。没有基地 / 项目：去主数据页，本切片不代建。

---

## 1. 业务是什么

交主机厂的是 **供货总成（至少有一个一级件带内部号的 L0）**。采购要管的不是这层容器，而是能单独向二级买、且能在 ERP 对上号的一级件，以及「成品就是一张板」的退化供货件。

| 列入采购对象 | 树上的样子 | 对人展示 |
|--------------|------------|----------|
| 退化供货件 | **仅 L0**。没有子件；**或**全部 L1 都没有内部号 | 退化供货件 |
| 分总成 | L1 **有内部号**，下面有 L2（所属 L0 不是退化供货件） | 分总成 |
| 冲压件 | L1 **有内部号**，下面没有孩子，且是板料（所属 L0 不是退化供货件） | 冲压件 |

L0 永不因 L2 带内部号而变成结构化总成：只看一级件。退化供货件名下的 L1 / L2 **不单独列入**。L2 跟在分总成下，**不单独列入**。L1 **没有内部号** 不是采购对象，进 **核对区（标准件/胶等）**，例如芜湖 T13J 的 `FQ114D0612T21F19E`（弧焊焊接螺柱与盖形螺母组合件）、`B11-4102613`（点焊胶）。

主机厂不允许把带内部号一级件的 L0 整层外发：**这类 L0 永不列入采购对象**。备注写了「凸焊总成供货」也不列入，只进 **核对区（异常）**。全部 L1 无内部号的 L0 按退化供货件列入，不进异常。

---

## 2. 分类规则（列入靠结构 + 一级件内部号）

子节点 = 同 snapshot 下至少一行 `parent_id = 本节点.id`。  
有内部号 = `internal_number` 去空白后非空。  
**一物一码在材料清单上传时已拦**（`validate_internal_number_uniqueness`）：有内部号的行，同一零件号只能对应一个内部号，同一内部号只能对应一个零件号；生成清单不要再写第二套闸。空内部号不参与（标准件/胶等）。

**退化供货件只针对 L0**，不针对 L1 / L2。

| `object_kind` | 条件 | 对人展示 |
|---------------|------|----------|
| `l0_degenerate` | `level=0`，且无子节点 **或** 全部 **L1** 都没有内部号（不看 L2） | 退化供货件 |
| `l1_subassembly` | `level=1`，**有内部号**，且有子节点，且所属 L0 **不是** 退化供货件 | 分总成 |
| `l1_stamping` | `level=1`，**有内部号**，无子节点，且是板料冲压件（§3），且所属 L0 **不是** 退化供货件 | 冲压件 |

| 不列入采购对象 | 落库 `section` | 对人展示 |
|----------------|----------------|----------|
| `level=0` 且至少有一个 L1 带内部号 | 默认不落行；备注含委外话术 → `anomaly` | 异常 |
| 退化供货件名下的 L1 / L2 | 不落行 | — |
| `level=2` | 不落行 | — |
| L1 没有内部号（所属 L0 非退化） | `other_leaf` | 标准件/胶等 |

列入 **禁止** 看：焊接原文有无、备注关键词、年度零件价有无行。这些最多当行字段或告警。L1 内部号 **决定** 该级是否采购对象，并决定 L0 是否退化。

---

## 3. L1：有内部号才可能是采购对象

无内部号的 L1 **一定不是** 采购对象（进核对区），不论名称像不像冲压件。T13J 例：`FQ114D0612T21F19E` 弧焊焊接螺柱与盖形螺母组合件、`B11-4102613` 点焊胶。

有内部号的 L1 叶子再把 **板料** 和 **标准件 / 胶 / 塑料** 分开：

认 `l1_stamping`（顺序，命中即停）：

1. `node_role = make`
2. `thickness_mm` 非空
3. 现网 `resolve_manufacturing_category(...) == "stamping"`

有内部号且不是冲压件的 L1 叶子 → `section=other_leaf`。T13J 叶子焊接原文为 0，**不能**用焊信当冲压件条件。

---

## 4. 退化供货件：全部列入，再标亚类

满足 §2 的 L0 **全部** `section=object` 且 `object_kind=l0_degenerate`（无任何子件，或全部 L1 无内部号）。树上可以有孩子，孩子 **不** 再列入采购对象。亚类只读，不改变是否列入：

| `degenerate_subtype` | 对人展示 | 规则（看原文，不编工艺） | T13J |
|----------------------|----------|--------------------------|------|
| `special_process` | 特殊工艺 | `weld_info` 或 `remark` 含电泳 / 面积 / 黑漆 / 喷粉 / 电镀 | 6 |
| `stamping_blank` | 冲压毛坯 | 其余 | 8 |

无工艺 ≠ 电泳，也 ≠ 不列入。外发还是自制，用行上的 `confirm_status`。生成摘要列出两个亚类件数；冲压毛坯可发货，无焊信则不编处理费，不因此否决检测。

---

## 5. 行上带出的字段（展示，不参与列入）

生成时从节点 **抄一份快照** 落到行上。树仍是分类真相；再生成按当时的树重算。

| 列 | 来源 |
|----|------|
| `weld_info` / `remark` | 节点原文 |
| `has_outsource_remark` | 备注含约定词则为真（提示，不是开关） |
| `material` / `thickness_text` / `material_mill` | 材料列；厂家是钢厂/紧固件商/胶商，**不是**二级冲焊厂 |
| `parent_part_number` / `parent_part_name` | 直接父件（L1 即供货总成；退化供货件为空） |
| `internal_number` | 本行节点内部号（可空；业务上当 ERP 编号）。不是 L0 内部号。列表弱化展示 |
| `l0_part_number` / `l0_part_name` | **核对凭据**：所属供货总成零件号/名称。L1 沿父上溯到 L0；退化供货件、异常 L0 **填自身**。列表、导出必带，不要让人只对着本行零件号对材料清单 |
| `excel_filename` / `excel_row` | **核对凭据**：导入时的 **原始 Excel 文件名**、**Excel 界面行号**（1-based，与打开原件看到的行号一致）。从 `bom_nodes` 抄，列表/导出必带 |
| `excel_sheet_name` | 来源工作表名（节点有则抄）。多表时和行号一起对原件 |
| `child_count` | 直接子节点数 |
| `source_node_id` | `bom_nodes.id`；同一零件号可出现在多棵树上 |
| `data_gap` | 可空。退化供货件材料/料厚/厂家全空 → `l0_material_missing` |
| `alert_code` | 可空。§7.4 告警码，不否决列入 |

约定词（仅打标，可按项目补）：`凸焊总成供货`、`总成供货`、`冲压单件供货`、`单件供货`、`黑漆件供货`、`电泳`。

本文不解析、不猜测二级供应商名称。行上 **禁止** 存单价、一口价。合同对方由采购 **点选** 供应商主数据，见指定供应商设计，**禁止**用 `material_mill` 或年度价厂名顶替，禁止自由填厂名。

---

## 6. T13J 金标准

解析口径与现网 `node_parser` 一致：A 列非数字即停。

| 树上 | 件数 | 采购对象清单 |
|------|------|----------------|
| L0 | 44 | — |
| L0 有子件 | 30 | 其中全部 L1 无内部号的 → `l0_degenerate`；其余不进 `object` |
| L0 无子件 | **14** | 全部 `l0_degenerate` |
| L1 有内部号且有子件 | 以现网为准 | `l1_subassembly` |
| L1 无内部号 | 以现网为准 | 核对区 `other_leaf`（如点焊胶、焊接螺柱组合件）；不进采购对象 |
| L2 | 108 | 不落行 |

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
|{无子件或全部 L1 无内部号的 L0}|  == |object_kind=l0_degenerate|
|{l0_degenerate}|  == |special_process| + |stamping_blank|
|{结构化总成下、有内部号且有子件的 L1}|  == |object_kind=l1_subassembly|
|{结构化总成下 L1 叶子}|  == |有内部号的冲压件| + |无内部号叶子（核对区）|
```

第三条、第四条只统计 **所属 L0 不是退化供货件** 的 L1。无内部号的 L1 **不得** 出现在采购对象区。退化供货件名下的 L1 不落行。  
亚类必须盖住全部退化供货件；**冲压毛坯件数可以非零**（T13J=8），不因此否决检测，也不编成电泳。

生成日志成功摘要在采购对象计数下写亚类件数，并加一行中性说明：`冲压毛坯 N 件（可发货；无焊信则不编处理费）`。毛坯发货是正式交件方式。不点名零件，不写成「已按毛坯供货」，不因此否决检测。

### 7.2 互斥

同一 `source_node_id` 只出现在一行。  
至少有一个 L1 带内部号的 L0、全部 L2、无内部号的 L1：`section=object` **零行**。退化供货件（可有无内部号的一级件）**可以**在采购对象区。

### 7.3 结构对账

| 检查 | 合格 |
|------|------|
| `l1_subassembly` 的 `child_count ≥ 1`，孩子全是 L2 | 是 |
| `l1_stamping` 的 `child_count = 0` | 是 |
| `l0_degenerate` 的全部 L1 都没有内部号 | 是（`child_count` 可以为 0） |
| `section=object` 的 L1 必须有内部号 | 是 |
| 每个 `section=object` 的 L1，父节点是带内部号一级件的 L0 | 是 |
| 每一行 `l0_part_number` 非空（退化供货件 / 异常 L0 为自身） | 是 |
| 每一行能从节点抄到 `excel_filename` 与 `excel_row` | 是（抄不到则告警，不挡列入） |

### 7.4 告警（不否决 `qa_passed`）

| `alert_code` | 含义 |
|--------------|------|
| `l0_outsource_remark` | 子件带内部号的 L0 备注含「凸焊总成供货」等；**仍不列入采购对象** |
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
无直接下游时覆盖导入会 **删旧 snapshot 再建**，清单随材料清单一起没，必须对新 snapshot **再生成**。该版本已有采购对象清单或焊接工艺拆解时 **禁止** 覆盖导入 / 删除材料清单（须升 BOM 版本，或先删这些直接下游）。一期 **不** 把确认迁到新 snapshot（`source_node_id` 已变，对错行的风险大于省勾选）。

### 8.2 清单头 `bom_procurement_object_lists`

一 snapshot 至多一份清单。唯一键：`snapshot_id`。

| 字段 | 业务含义 |
|------|----------|
| `snapshot_id` | 哪一版材料清单 |
| `location` / `vehicle_model` / `bom_version` | 从 snapshot 冗余，列表筛选不必总 join。界面「项目」= `vehicle_model`。新生成抄 snapshot；历史允许别名/小写（§13） |
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
| `internal_number` | 从该行节点抄内部号（可空；业务上当 ERP 编号）。**不是** L0 内部号。列表弱化展示，方便找不到供应商时去 ERP 联查 |
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

入口：选定 **基地 + 项目 + BOM 版本**（服务层解析当前 `snapshot`），点 **生成**（对齐焊接工艺拆解，不是上传 Excel）。口语里可以说「把采购对象从树上生成出来」，界面和表名不要写「抽取」。写门禁见 §13，**不要**把生成写成「传 BOM」那套墙钟 `require_introducible`。

1. 读该 snapshot 全部 `bom_nodes`，纯函数分类 + 检测。  
2. **一个事务**：删该 snapshot 旧清单头（级联删行）→ 写新头 + 新行。  
3. 同一 snapshot 再生成：按 `source_node_id` **带回** 旧行的确认三态 / 确认人时 / 备注。新出现的节点 `pending`；已不在树的确认丢弃。合同对方 `supplier_name` 的带回见 [指定供应商](bom-procurement-object-supplier-design.md)。  
4. 无直接下游时覆盖导入换了 snapshot：旧清单已随旧 snapshot 删掉，新生成全是 `pending`。已有采购对象或焊接拆解则材料清单禁止覆盖。  
5. 写一条 `bom_procurement_object_generate_logs`（成功或失败终态）。

检测未通过：照样提交，`qa_passed=false`。不要为了「名单好看」只写一半采购对象。

**已审核锁定：** 该 snapshot 下只要有一行 `audit_status=approved`，禁止再生成覆盖（`BusinessException` `code=409`）。须先 **批量反审核**。不要把已审行悄悄跳过再抽一半。设变后的增量插行不走本条，见 §14。

一期 BOM 节点量级 **同步生成**（无异步任务、无 processing 锁）。生成页有进度条是前端等待 HTTP，不是后台 worker。

### 8.5 确认、审核、CRUD

对齐现网 **年度零件价 / 焊接单价** 列表：删除、审核、反审核 **只走批量、按范围、意见必填**。禁止单条审核/反审核/删除 API，禁止操作列做这三件事。

**确认（业务勾选，不是审核）**

- 只改 `section=object` 的 `confirm_status`（待定 / 外发 / 自制）和确认备注。
- 不改 `object_kind`、核对凭据、材料快照。
- `qa_passed=false` 或 `approved` 时拒绝（已审须先批量反审核）。有效期改造后：`qa_passed` 取 **该月命中树根** 上的 7.1–7.3，不读清单头整包字段，见 §14。
- 确认允许 **单条**（操作列改外发/自制）：这是「这一件怎么买」，不是锁定。

**删除 / 审核 / 反审核（只批量，按清单范围）**

与年度零件价「按基地 + 年」相同：body 带 **范围键**，不传行 id、不按勾选。

| 项 | 口径 |
|----|------|
| 范围 | 一份清单 = 基地 + 项目 + BOM 版本（对应一个 snapshot）。有效期改造后 **加年+月**：只打该月命中树根下的行，见 §14 |
| 入口 | 列表工具栏按钮 + 抽屉；**审核意见 / 反审核原因必填**（`min_length=1`） |
| 删除 | 按范围：无年+月且无 `approved` 时 **`delete_list` 清清单头**（行级联，与 SOP 生成覆盖一致）；有 `approved` 或已带年+月时只删范围内 `pending` 行（含标准件/胶等、异常），已审与其它月行跳过，返回 `skipped_approved_count` |
| 审核 | 把范围内 `section=object` 且 `pending` 改为 `approved`；已审跳过；意见写入 `audit_remark` |
| 反审核 | 把范围内 `section=object` 且 `approved` 改回 `pending`；非已审跳过；原因写入 `reverse_audit_remark` |
| 锁定 | `approved` 禁止改确认、禁止 SOP 再生成覆盖 |
| 检测 | 该月命中树根上 7.1–7.3 未过则拒绝审核（可导出、可删 pending 以便重生成）。不拿清单头整包 `qa_passed` 当本月门禁 |

不要求先确认外发才能审。列表要能筛未确认已审。

无已审时整单删头，不必重算。有已审时删 pending 后重算清单头计数；完备性被破坏则 `qa_passed=false`。核对区不审核、不反审核。有效期改造后日常删除走 §14.4（按命中树根），不要靠这段整包重算当本月账。

**CRUD**

| 字母 | 做什么 | 不做什么 |
|------|--------|----------|
| C | **生成** 整份清单 | 手填一行乱入分类 |
| R | 列表分页、summary、单条详情、生成历史 | |
| U | 单条改确认（待审） | 改总成号、Excel 行号、分类；单条审核 |
| D | **仅批量删除**（按范围；无已审清清单头，有已审跳过） | `DELETE /items/{id}`；操作列删除 |

**导出 Excel**

- 与列表同一套筛选，不分页。
- 三张工作表（采购对象 / 标准件及胶等 / 异常），无封面。必含原件文件名、行号、供货总成、本行零件、对象种类、确认、审核。
- 冻结 `I6`；打印标题 `A:H`。相邻行相同供货总成零件号+名称时合并 G/H。
- 色板与冲压模具费导出同族（靛蓝标题 / 石板分组 / 品牌红判定）。
- 零件号后：**短码**（数字末四位，核对焦点，石板色加粗）；再 **内部号**（灰色弱化）。列表仍无「关注点」列。
- `qa_passed=false` **仍允许导出**（标明未通过）。

### 8.6 分层

```text
Router  → ProcurementObjectService 门面（查询 + 委托）
              ├── GenerateService      写门禁 + 分类 + 覆盖写
              ├── AuditService         单条确认 / 按范围批量审核·反审核·删除
              ├── GenerateLogService   成功进生成事务；失败 rollback 后单独提交
              ├── ExportService        与列表同一套筛选，不分页
              └── classify / labels / mapping  纯函数
                    └── 只读 BomNodeRepository / BomSnapshotRepository
```

禁止 Router 写 SQL、调 Parser、调 `LocationService` / `VehicleModelService`。  
禁止生成时读年度价、焊接拆解、冲压价、供应商主数据。  
Parser 不参与（树已在 `bom_nodes`）。

路径：

```text
app/models/bom/procurement_object.py
app/models/bom/procurement_object_generate_log.py
app/repositories/bom/procurement_object_repository.py
app/services/bom/procurement_object/   service · generate_service · audit_service · generate_log_service · export · classify · labels · mapping
app/routers/bom/procurement_object.py
app/schemas/dto|vo/bom_procurement_object_*.py
static/js/features/bom/procurement-object/
```

对人展示文案（勿在页面/导出再写一套）：

- `app/services/bom/procurement_object/labels.py`
- `static/js/features/bom/procurement-object/labels.js`

API 前缀：`/api/bom/procurement-objects`。生成与批量范围键均为 **基地 + 项目 + BOM 版本**（不是客户端传 `snapshot_id`）。有效期改造后列表 / 导出 / 批量写 **加 `year` + `month`**（§14）。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/generate/prep-stats` | 生成页 KPI：节点 / 将列入 / 标准件/胶等 / 异常 / 已审锁定 |
| POST | `/generate` | body：范围；有已审行则 409。**合册落地时**含失效树/合册树的 snapshot 亦拒绝，见 §14 |
| GET | `/generate/logs` | 生成历史分页 `page`+`size` |
| GET | `/generate/logs/{log_id}` | 过程全文 |
| GET | `/summary` | 当前范围；有效期改造后计数/检测按该月命中树根（尚未生成则 404） |
| GET | `/` | 分页 `page`+`size`；筛范围 / section / object_kind / confirm_status / audit_status / part_number / l0_part_number / excel_row；`section` 空 = 全部。有效期改造后加 `year` / `month` / `include_expired` |
| GET | `/items/{id}` | 单条详情 |
| PATCH | `/items/{id}/confirm` | 单条确认三态（待审） |
| POST | `/batch-approve` | **按范围** 批量审核；`audit_remark` 必填；禁止 ids |
| POST | `/batch-reverse-audit` | **按范围** 批量反审核；`reverse_audit_remark` 必填；禁止 ids |
| POST | `/batch-delete` | **按范围** 整单删除：无已审清清单头；有已审只删 pending（含核对区）并跳过；禁止 ids |
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

禁止另起 `style.css` 业务 class。生成页 KPI 下可有一行 9px 灰色说明（退化供货件口径），禁止卡片、黄条、加粗抢主按钮。

### 9.2 页面内容

列表页签：**全部**（默认，不传 `section`）| 采购对象 | 标准件/胶等 | 异常。HUD 展示采购对象条数、标准件/胶等、待审、已审（有效期改造后 = 该月命中树根，与结构树同一 as_of）。该月 7.1–7.3 未过用错误文案，不要静默当成功、不要用清单头整包 `qa_passed`。

筛选条：现网范围键之外，有效期改造后加年、月（与结构树同一默认）；开关「含已失效」默认关。列表须有生效日期、失效日期两列，**从所属树根读**，与结构树 L0 同值；对象行不能改这两项。

工具栏：**批量审核 / 批量反审核 / 批量删除** + 导出 Excel。抽屉展示当前清单范围（基地 · 项目 · 版本；有效期改造后加年+月），意见必填。删除口径见 §8.5 / §14。禁止勾选行再批量。

**核对列：** 列表与导出须能直接对回原件：

1. **原件**：`excel_filename`（页头再用清单的 `source_filename`）
2. **行号**：`excel_row`（Excel 界面 1-based）
3. **供货总成**：`l0_part_number` / `l0_part_name`
4. **本行**：零件号 / **短码**（数字末四位）/ 内部号（弱化）/ 名称
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
| 覆盖导入 | 有采购对象或焊接拆解则禁止；无直接下游才删 snapshot 并级联删清单 |
| `node_parser` | 生成不改解析；材料落不到退化供货件时打 `data_gap` |
| `manufacturing_category` | L1 叶子是否冲压件，复用，不新开词典 |
| 焊接工艺拆解 | **不读** |
| 年度零件价 | **不读** |
| 基地 | 生成 `require_enabled`；列表筛 `list_registered` + 查询 `expand_for_query`。本表不加基地外键 |
| 项目 | 列表筛 `list_registered`。生成不 `require_introducible`。本表不加项目外键 |
| 供应商 | 生成不读、不猜。行上指定对方见独立设计 |

---

## 11. 做 / 不做

| 做 | 不做 |
|----|------|
| 按树列入三类采购对象并落库 | 用备注 / 焊信 / 年度价决定列不列入 |
| 清单头记检测结果；失败也落库 | `qa_passed=false` 仍当「名单已合格」 |
| 标准件/胶等 + 异常进核对区 | 把子件带内部号的供货总成、L2 写入采购对象 |
| 同 snapshot 再生成带回确认；已审禁止覆盖 | 覆盖导入后自动把确认对到新 `source_node_id`；设变后仍走生成页整表重写；对象行另写生失效；清单头整包数当本月账 |
| 确认外发/自制（单条）；批量审核/反审核/删除（按清单，有效期后加月） | 单条审核、单条删除、按 id 勾选批量；手建一行改分类；Excel 导回当审核 |
| 生成页/列表页抄零件价格计算 + 一览 | 抄年度零件价列表壳；自创第三套样式 |
| 已审禁止改确认/删除/再生成 | 算单价、应成本 |
| 退化供货件全部列入，再标亚类 | 无工艺就不列入，或编成电泳 |
| 同一零件号多行都保留 | 按零件号去重 |
| 对人展示走 `labels` | 页面再写「其它叶子」「退化 L0」当产品文案 |
| 生成前过基地 `require_enabled`；列表基地筛主数据 | 本切片代建基地/项目；给清单头加基地/项目外键 |
| 界面写「项目」 | 再写「车型」当产品文案 |

---

## 12. 相关代码与文档（本切片）

| 位置 | 角色 |
|------|------|
| `app/models/bom/node.py` | `level` / `parent_id` / `node_role` / `weld_info` / `remark` / `excel_row` |
| `app/parsers/bom/node_parser.py` | 树怎么进库；L0 材料是否落地 |
| `app/common/bom/manufacturing_category.py` | L1 叶子是否 `stamping` |
| [welding-process-breakdown-design.md](welding-process-breakdown-design.md) | 拆解；生成清单时不读 |
| `app/services/bom/bom_upload_service.py` | 覆盖导入前检查直接下游；无下游才删 snapshot（清单级联没）。落库前拦一物一码 |
| [bom-annual-part-prices-design.md](bom-annual-part-prices-design.md) | 价表；本文不读 |
| [location-design.md](../masterdata/location-design.md) | 基地；生成写门禁、列表筛 |
| [vehicle-model-design.md](../masterdata/vehicle-model-design.md) | 项目；列表筛；本文不是下一跳 |
| [supplier-design.md](../masterdata/supplier-design.md) | 合同对方主数据；生成不读 |
| [bom-procurement-object-supplier-design.md](bom-procurement-object-supplier-design.md) | 行上指定合同对方（已落地；可空 FK → 供应商） |
| [bom-procurement-object-supplier-upload-design.md](bom-procurement-object-supplier-upload-design.md) | 按清单范围 Excel 批改对方（已落地） |
| [assembly-costing-design.md](../costing/assembly-costing-design.md) | 下游应成本；集合以本清单为准 |
| [procurement-contract-report-design.md](../costing/procurement-contract-report-design.md) | 签约横表（已落地）；只读本清单 + 应成本 |
| [bom-process-die-effective-period-design.md](../engineering-change/bom-process-die-effective-period-design.md) | 树根生失效；本清单列表 as_of |
| [part-number-revision-design.md](../engineering-change/part-number-revision-design.md) | 设变增量带出（§14） |
| `static/js/features/costing/stamping-part-cost/calc/` | 生成页 UI 对照 |
| `static/js/features/costing/stamping-part-cost/list/` | 列表页 UI 对照 |

---

## 13. 基地 / 项目（主数据）

分类规则不改。本节只补 **写谁、筛谁、外键挂谁**。细则不在本文重写，调上游设计。

引用保护（宪法 §4.3）：**子声明、父不知；只拦直接下游。** 项目的下一跳是 `bom_snapshots`，不是本清单。清单头只声明 `snapshot_id → bom_snapshots.id`（`ON DELETE CASCADE`，同切片附属结果）。生成日志、清单行上的 `location` / `vehicle_model` 字符串副本 **不加** 基地外键、**不加** 项目外键。项目 Model 禁止 `relationship` 指向本表。

### 13.1 已定规则

| # | 规则 |
|---|------|
| O1 | 没有已启用基地，不能新生成。`LocationService.require_enabled`。找不到 / 已禁用 → 去 `#/location`，不代建 |
| O2 | 生成不是传 BOM。BOM 上传已过墙钟 `require_introducible`。本文 **禁止** 再套一套 `require_introducible`。已失效项目：已有 snapshot 仍可生成 / 再生成；没有 snapshot 不能生成 |
| O3 | 不立项。代号对不上已有 snapshot → 「未找到对应材料清单」，去焊接工程上传，不去项目一览表代建 |
| O4 | 库字段仍 `vehicle_model`。界面、Toast、抽屉、导出页头写 **项目**，不要写车型 |
| O5 | 代号查找前 `normalize_vehicle_model`（含大写）。`t13j` 与 `T13J` 同一代号。不做项目别名展开（项目设计 P14） |
| O6 | 清单头 `location` / `vehicle_model` / `bom_version` **抄 snapshot**（现网已如此）。不在生成时改写 snapshot，也不为迁就外键改历史清单头 |
| O7 | 列表 / 导出：基地选项 `list_registered`；选了基地后查询条件 `expand_for_query`（命中历史「×基地」）。项目选项 `VehicleModelService.list_registered`（先选基地；未选则各基地代号并集）。**禁止**本表 `DISTINCT location` / `DISTINCT vehicle_model` 当身份选项。版本仍列本范围已有 BOM / 清单版本（存在性，不是身份）。HUD 计数仍扫本表 |
| O8 | 生成页下拉：基地 `list_enabled`（写路径）。项目 / 版本 = 该基地下 **已有** `bom_snapshots` 的 cascade（没有材料清单不能生成）。废止写死四基地。现网 `/api/bom/filters/cascade` 须把基地源改成主数据，不要从本切片 DISTINCT |
| O9 | 确认 / 审核 / 反审核 / 删除是改已有清单，不过 `require_enabled`。基地禁用后已有清单仍可查、仍可反审核以便清理。新生成仍走 O1 |

### 13.2 生成：怎么找到 snapshot

1. `canonical = LocationService.require_enabled(raw_location)` → 规范名。不过则硬停。  
2. `code = normalize_vehicle_model(raw_vehicle_model)`。空 / 占位符 → `BusinessException`。  
3. 先 `get_by_unique_key(canonical, code, bom_version)`。没有：对 `expand_for_query(canonical)` 里每个别名再找（历史 snapshot 可能仍是「青岛基地」）。都没有 → `NotFoundException("未找到对应材料清单")`。  
4. 清单头抄 **该 snapshot** 的 `location` / `vehicle_model` / `bom_version` / `source_filename`。新行不把别名改写成规范名。  
5. 其余覆盖写、带回确认、已审 409：§8.4 不变。设变增量不走本入口，见 §14。

现网已做：第 1 步 `require_enabled`；第 3 步只按用户所选字符串 `strip` 精确匹配（未 expand、未 normalize）。第 2 / 3 步是落地缺口。

prep-stats 是读：不强制 `require_enabled`（禁用基地仍可看「将列入」）。文案「请选定基地 / 项目 / 版本」。

失败日志：业务事务 `rollback` 之后 **单独提交** 一条 `failed`（现网 `persist_failed`）。成功日志进同一生成事务。

### 13.3 读

查询按库里的字符串。用户选规范名「青岛」时，条件展开为规范名 + 别名，才能命中历史清单头 `青岛基地`。项目筛双方先 `normalize`；对不上历史小写代号，接受（不写第二套查询）。

筛了一个还没生成的项目 → 空表，不是丢数据。

### 13.4 外键（只此一张）

| 表 | FK | 说明 |
|----|----|------|
| `bom_procurement_object_lists.snapshot_id` | → `bom_snapshots.id` `ON DELETE CASCADE` | 同切片附属结果；删 snapshot 清单没 |
| 清单行 `list_id` | → 清单头 `CASCADE` | 附属行 |
| 生成日志 | **无** 指向 snapshot / 项目 / 基地 | 与计算日志同类，间接副本 |

禁止：清单头再声明基地 FK、项目复合 FK。拦「项目还能不能删」的是 `bom_snapshots`，不是本表。

---

## 14. 跟树根有效期（未落地）

对象行 **不加** 生失效四列。某月在不在、数多少、检过没过、能不能审，**完全等于**所属 L0 树根该月命不命中。与结构树同一 `as_of`、同一默认月。L0 PATCH 改期后对象立刻跟，无须改对象行。禁止对象行另存四列、禁止清单头整包计数当本月账。

作业入口见 [工程变更](../engineering-change/part-number-revision-design.md) §4.4；树根改造见 [有效期](../engineering-change/bom-process-die-effective-period-design.md)。分类规则、一 snapshot 一份清单、`(list_id, source_node_id)` 唯一键：**不改**。

### 14.1 按月：只打命中树根

`year` + `month` 与结构树同一默认。`include_expired` 默认关；打开时行上仍展示 **树根** 的生效/失效，避免当成在产。

先收集该月命中的 L0，再收子树 `source_node_id`，再取对象行。7.1–7.3、HUD、summary、导出、确认门禁、批量审核/反审核/删除、核价覆盖，全部只用这一批。

| 入口 | 该月做什么 |
|------|------------|
| 列表 / HUD / 导出 | 只出命中树根下的行。生效/失效两列 = 所属 L0，与结构树同值、同 `YYYY-MM`。同一零件号新旧两行靠月分开 |
| 单条确认 / 指定供应商 | 仍按行 `id`；已审拒绝。该月检测未过拒绝确认 |
| 批量审核 / 反审核 / 删除 | 范围键 **加上年+月**，只打命中树根下的行 |
| 核价覆盖检查 | 只要求该月命中树的节点都有对象行 |

未选月：与结构树同一默认。禁止默认把 AA/AB 并排当本月账。

清单头 `l0_count` / `qa_passed` 仍是 SOP 生成时的整包痕迹，**列表与门禁不读**。本月数现场按命中树根算。

### 14.2 SOP 生成 vs 设变插行

| | SOP / 无设变 | 工程变更种新树 |
|--|----------------|----------------|
| 谁触发 | 生成页「开始生成」（当时林子里树根时段相同） | 设变导入同一事务，只扫新种的那一棵 |
| 写 | §8.4 删头重写；按 `source_node_id` 带回确认与供应商 | **不删头、不碰旧行**；按现网规则分类后 **插新行** |
| 已审 | 有一行已审 → 409 | 不挡；旧已审行不动 |
| 日志 | `bom_procurement_object_generate_logs` | 不写一条冒充整单覆盖的生成日志；件数记在变更单 |

现网「开始生成」仍按 §8.4 整 snapshot 删头重写。**合册落地时**才收窄：该 snapshot 一旦有已失效树根、或树根生效月不是项目 SOP 开始月 → 拒绝（即使没有已审）。按 `source_node_id` 带回 **抄不到** 新树上的同号对象。缺对象走工程变更重传，不在生成页做「只补该月」。合册种树与插行在 **同一事务**，不走本页 `generate`。SOP 纠错改期请在种树前做；种树后改期走结构页 L0。见 [合册 §4.6](../engineering-change/part-number-revision-design.md)。

### 14.3 从被替换旧树抄确认

只匹配 **被替换的那一棵旧树**（本例 3086AA），禁止扫 snapshot 里其它总成的同号。新行的命中月跟 **新树根**，不继承旧树根时段。

| 新树节点 | 落行 |
|----------|------|
| 采购对象，旧树有同行（同 `part_number` + `section` + `object_kind`） | 插新行。抄确认三态 / 确认人时 / 确认备注 / `supplier_name`。**不抄** `audit_status`（新行待审）。`l0_*`、父件、Excel 行号、材料快照抄 **新节点** |
| 采购对象，旧树无同号，但是改图字母版本换号（去掉末两位后相同、字母版本进一位），旧树有旧号同行且 `object_kind` 不变 | 插新行；确认 / 厂家 **从旧号同行抄**（树上号关系；此件不装祖先升号同样适用）。**不抄** `audit_status` |
| 采购对象，旧树无同行且无字母版本可对（增加零件；`object_kind` 变了） | 插新行，`pending`，供应商空。禁止从钢厂列 / 备注 / 年度价猜 |
| 该 snapshot 尚无清单头 | 合册 **先建空头再插行**（不走 generate），见合册 §4.4 |
| `other_leaf` / `anomaly` | 插新行；无确认可抄 |
| `object_kind` 变了 | 当新号，不抄确认 |

抄来的 `supplier_name` 不跑 `require_enabled`（与 §8.4 带回相同）；全称已不在 `suppliers` 则该行落空，不让整单 `IntegrityError`。插完 **不** 把清单头改成全林计数。

同一零件号可同时有旧树行与新树行。指定供应商批传仍按现网整清单、按零件号去重——同号多行时 **拒绝批传**，改走行上点选。细则仍在供应商上传设计，落地时改那篇。

### 14.4 删除

带年+月：只删该月命中树上的 `pending`（含核对区）；已审与未命中树的行跳过；**不清清单头**。  
不带年+月：维持 §8.5（无已审才 `delete_list`）。设变之后不要用不带月的整单删除当日常。

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
| 2026-09-02 | 手填合同对方与签约报表拆出独立设计；本文仍禁止生成时猜供应商、禁止存单价。 |
| 2026-09-08 | 补基地/项目主数据：生成 `require_enabled`、不套 `require_introducible`、清单不是项目下一跳；列表筛主数据；界面「项目」。指定对方改点选供应商主数据（见独立设计）。 |
| 2026-09-08 | 清单行抄节点 `internal_number`；列表弱化展示，供找不到供应商时 ERP 联查。 |
| 2026-09-08 | 导出零件号后加短码（数字末四位，核对焦点）与内部号（灰色弱化）；冻结 `I6`，合并供货总成 G/H。 |
| 2026-09-09 | 一物一码在材料清单上传拦（有内部号的零件号↔内部号一一对应）；本切片生成不再复检。 |
| 2026-09-16 | 批量删除覆盖核对区（标准件/胶等、异常）；审核 / 反审核仍只针对采购对象。 |
| 2026-09-16 | 无已审时批量删除连清单头 `delete_list`（与生成覆盖一致）；有已审仍只删 pending 并重算头。 |
| 2026-09-16 | §14：采购对象严格跟树根有效期；检测/计数/审核只对该月命中树；列表展示树根生失效；设变只给新树插行。 |
| 2026-09-16 | 设变插行与合册同一事务，不走 `generate`；种树后生成页保持拒绝。 |
| 2026-09-17 | 收口：生成页拒绝整包是 **合册落地时** 才改的现网门禁；落地前仍按 §8.4 整 snapshot 覆盖。 |
| 2026-09-17 | §14.3：改图字母版本换号允许从旧号抄确认与厂家（与合册少手工对齐）；增加零件仍 pending。 |
| 2026-09-17 | §14.3：无清单头时合册先建空头；字母版本抄确认亦适用于此件不装祖先升号。 |
