# 采购对象指定供应商 — 设计说明

> **状态：已落地。** 不改分类规则、不算价。  写入路径见供应商第二期。  
> 切片：**`bom`**（采购对象清单的行上动作）。  
> 上游清单：[bom-procurement-objects-design.md](bom-procurement-objects-design.md)。  
> 对方身份：[supplier-design.md](../masterdata/supplier-design.md)（**点选本文，禁止自由文本**；写门禁 S12）。  
> 下游签约报表：[procurement-contract-report-design.md](../costing/procurement-contract-report-design.md)。  
> 硬约束：[architecture.md](../architecture.md)。  
> 年度价 `supplier_name` **不是**本字段：报价档案，不跑 `require_enabled`（供应商设计 S15）。

---

## 0. 一句话

**集合上指定合同对方。** 采购对象清单已经回答「买哪些」和外发/自制；本设计只在 **采购对象行** 上写下二级供应商 **规范全称**，供按厂分包、签合同。仍不管价、不管合同怎么起草。

选项只来自供应商主数据。找不到：停止，去 `#/supplier-list` 补。禁止自由输入，禁止从备注 / 钢厂列 / 年度价发明对方。

写门禁与 [supplier-design.md](../masterdata/supplier-design.md) **§6.0 / S12** 同一套：`SupplierService.require_enabled`。指定或改成非空才跑；清空、再生成带回不跑。供应商切片与工艺确认门禁已在第一期落地；**本页是供应商第二期必做**。禁止另写一套校验。

---

## 1. 为什么做

采购拿着清单分供应商、去签合同。没有「这一件外发给谁」，下游横表只能按件看，不能按厂出附件。

供应商跟 **BOM 版本上的那一行对象** 走，不跟核价月份走。换查询窗口只换金额列，不换对方。

| 已有 | 本设计补的 |
|------|------------|
| `confirm_status` 外发 / 自制 | 外发之后（或同时）指定谁做 |
| `material_mill` | 钢厂 / 紧固件商 / 胶商，**不是**合同对方 |
| 年度价 `supplier_name` | 价表报价来源，**不是**分包指定 |
| 总成卡 `vendor_name` | 该月命中年度价抄来的报价厂名，**不是**本字段 |

清单原文「不猜测二级厂名」仍然成立：系统不从备注解析供应商。本设计是采购 **点选主数据**，不是生成时猜，也不是自由填厂名。

初稿曾写「一期自由文本、不做主数据表」。供应商主数据已定：[supplier-design.md](../masterdata/supplier-design.md) 的 S3 / S5 **覆盖**那条。落地时改点选，不要再开第二套自由输入。

---

## 2. 落在哪一行

| 行 | 可否指定 |
|----|----------|
| `section=object`（退化供货件 / 分总成 / 冲压件） | **可以** |
| `other_leaf` / `anomaly` | **禁止**（不是采购对象） |

粒度：一份清单里一行对象 **至多一个** 供应商。一期不做一件对多家。

时间：无起止月。同一 `source_node_id` 在该 snapshot 上只有一个对方。

---

## 3. 字段

表：`bom_procurement_objects`（现网清单行，不加新表）。本行 **是** 供应商主数据的直接下一跳（[supplier-design.md](../masterdata/supplier-design.md) S16）：

```python
supplier_name: Mapped[str | None]  # String(100)
ForeignKey("suppliers.full_name", ondelete="RESTRICT", onupdate="RESTRICT")
```

**可空。** 未指定 / 清空 / 自制清空 = **`NULL`**，禁止存空串 `''`。`NULL` 不引用供应商，不挡供应商改全称、不挡删除。非空必须是规范全称。供应商父 Model **禁止** `relationship` 指向本表。

| 字段 | 类型 | 含义 |
|------|------|------|
| `supplier_name` | `String(100)`，**可空** | 合同对方 = 供应商主数据 **规范全称**。未指定 = `NULL` |

禁止：

- 存单价、一口价、合同号、有效期（那些不是集合的事）。
- 把 `material_mill` 抄进本字段。
- 存缩写或 ERP 代码（下游列一律规范全称；短名读主数据缩写）。
- 自由文本、页面内嵌创建。

写入前：

1. strip；空串 / 只空白视为 `NULL`（清空），**不**跑 `require_enabled`，写库必须是 `NULL` 不是 `''`。  
2. 非空 → `SupplierService.require_enabled`（已登记且已启用）。对不上 / 已禁用 → `BusinessException`，提示去 `#/supplier-list`，不代建。  
3. 落库只写 **规范全称**。别名 / 缩写命中同一条则通过，仍落全称。外键只保证全称在 `suppliers` 里，不管启用。

列表可旁注缩写；本行只存全称。

---

## 4. 与确认、检测、审核

对齐现网确认，不是第二套审核。

| 条件 | 指定 / 清空供应商 |
|------|-------------------|
| `qa_passed=false` | 拒绝（与确认相同） |
| `audit_status=approved` | 拒绝；须先按范围批量反审核 |
| `section≠object` | 拒绝 |
| `confirm_status=in_house` | **禁止非空**。改为自制时 **清空** `supplier_name` |
| `confirm_status=pending` | 允许先指定（待定也可以写对方）；签约报表默认不出待定 |
| `confirm_status=outsourced` | 允许空（待指定）或已填 |

不要求「必须先外发再指定」，也不要求「必须指定才能审核」。列表要能筛：未指定 / 已指定；外发且未指定是采购缺口。

已审锁定：禁止改确认、禁止改供应商、禁止再生成覆盖（现网已审规则不变，只把供应商列入「行上业务勾选」一并锁）。

供应商主数据禁用：不准 **新指定** 该对方；已写在行上的全称仍可查、导出。要改成别家：须该行待审，再点选已启用的供应商。

---

## 5. 生成带回

同 snapshot 再生成：按 `source_node_id` 带回现网已有的 **确认三态 + 确认备注 + `supplier_name`**。新节点 `supplier_name` 为 `NULL`。已不在树的指定丢弃。带回 **不** 再跑 `require_enabled`（历史全称可能已禁用；外键仍要求父行存在）。若该全称已不在 `suppliers`（删光后再生成的窗口）→ 该行落 `NULL`，**不要**让整次生成因 `IntegrityError` 失败。

覆盖导入换 snapshot：现网不迁确认，**也不迁供应商**（`source_node_id` 已变）。

---

## 6. API / 页面

仍走采购对象切片，不新开 Router 前缀。选项 **不另开** 供应商 CRUD HTTP：本切片 Service 调供应商切片。

| 方法 | 路径 | 说明 |
|------|------|------|
| PATCH | `/api/bom/procurement-objects/items/{id}/supplier` | 单条指定或清空。body：`supplier_name`（可空；`''` 与缺省当清空 → `NULL`；非空 = 全称或能解析到全称的缩写/别名，Service 收成规范全称） |
| GET | `/` 列表 | 增加筛 `supplier_name`（按规范全称）、`has_supplier`（是/否） |
| GET | `/export` | 采购对象工作表增加「供应商」列（规范全称） |

禁止：用 **列表导出** 文件导回当指定；按表 `id` 勾选批量改供应商；输入框自由打字。

按清单范围用 Excel 批改对方：独立上传页，见 [bom-procurement-object-supplier-upload-design.md](bom-procurement-object-supplier-upload-design.md)（窄表按零件号去重并对账；写门禁与本页 PATCH 相同）。

权限：沿用 `op:bom-procurement-object-list:update`（与单条确认同一操作码）。不新增权限码。

列表：操作列在确认之外增加指定供应商（**下拉**，选项 `list_enabled`；展示「缩写（全称）」，**value = 全称**）。已审行控件禁用。核对区行不出现该控件。找不到要的厂：Toast 深链 `#/supplier-list`，**不得**内嵌创建。

导出三表里，仅「采购对象」表有供应商列；标准件/胶等、异常不写。

前端风格仍对齐现网采购对象列表（HUD / `#FF1E27`），不新开一页。

落地时同步：[supplier-design.md](../masterdata/supplier-design.md) §4.1 第二期清单。权限沿用现网 `op:bom-procurement-object-list:update`，不新增供应商权限码。

---

## 7. 分层

```text
Router  → 现网 ProcurementObjectService（门面，可下沉 AuditService）
              └── 校验 qa / 审核 / section / 自制清空
              └── SupplierService.require_enabled（非空时）
              └── Repository 更新 supplier_name（规范全称或 NULL）
```

禁止：生成分类时读本字段；costing 回写本字段；从年度价/备注/钢厂列自动填；Router 调供应商 Repository。

---

## 8. 做 / 不做

| 做 | 不做 |
|----|------|
| 采购对象行点选一个已启用供应商，存规范全称；未指定 **`NULL`** | 自由文本、一件多家、合同状态机、空串 `''` |
| 再生成按节点带回（含已禁用的历史全称） | 覆盖导入后自动对到新节点 |
| 自制清空；已审锁定 | 用钢厂列或年度价厂名顶替 |
| 列表筛未指定 | 指定参与列入/检测 `qa_passed` |
| 找不到去 `#/supplier-list` | 本切片代建供应商；给本列存空串 `''`；`CASCADE` 改/删供应商时改清单行；另写一套厂名校验；用年度价 `supplier_name` 顶替 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-02 | 初稿：清单行 `supplier_name`；与确认/审核锁定对齐；签约报表只读本字段。 |
| 2026-09-08 | 覆盖「一期自由文本」：点选供应商主数据，落库缩写；禁用后不准新指定、历史行可查。 |
| 2026-09-08 | 写门禁锁死为供应商设计 `require_enabled`（S12）；深链 `#/supplier-list`。落库改为规范全称（与现网工艺确认一致），缩写只作点选旁注。 |
| 2026-09-08 | 纳入供应商第二期：工艺门禁已落地；本页未落地。明确与年度价档案（S15）分家。 |
| 2026-09-08 | 本表改为供应商直接下一跳：`supplier_name` 可空 FK `RESTRICT`/`RESTRICT`。NULL 不挡删/改主键。 |
| 2026-09-08 | 空串收 `NULL`；带回时父行已删则该行 `NULL`，不整单 FK 失败。 |
| 2026-09-08 | 打开 Excel 批改：禁止的是列表导出导回；窄表上传见独立设计。 |
