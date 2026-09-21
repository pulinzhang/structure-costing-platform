# 采购对象批量上传供应商

> **状态：已落地。** 范围与生成页同形：基地 + 项目 + **snapshot 头版本** → `get_by_unique_key` → 按 `snapshot_id` 取采购对象清单。下拉 `version_source=snapshot`，**不出 EC**。  
> 「版本」三义见[采购对象清单](bom-procurement-objects-design.md)：本页只用 **snapshot 头**，不问树根浏览。  
> 切片：**`bom`**（采购对象清单的批量写路径）。  
> 单条点选：[bom-procurement-object-supplier-design.md](bom-procurement-object-supplier-design.md)（已落地；本页不替代抽屉）。  
> 对方身份：[supplier-design.md](../masterdata/supplier-design.md) **S3 / S5 / S12**（禁止本页代建；非空仍 `require_enabled`）。  
> 集合 / 取件口径：[bom-procurement-objects-design.md](bom-procurement-objects-design.md)（改前必读第 7 条）。  
> 权限流程：[permission-design.md](../permission-design.md) §0。  
> 溯源：[file-trace-design.md](../file-trace/file-trace-design.md)。  
> 硬约束：[architecture.md](../architecture.md)。

覆盖指定设计 §6 旧禁令「禁止 Excel 导回当指定」。单条 PATCH 仍在；本页是 **按基地+项目的 Excel 批改**，不是第二套供应商主数据。

---

## 0. 一句话

**先选定基地 + 项目 + snapshot 头版本，下载窄表，只改供应商列再传回去。** 三键必选，与生成页同一把钥匙：`get_by_unique_key` 找材料清单，再 `get_list_by_snapshot_id` 取采购对象。写入规则与单条指定完全同一套：只改 `section=object` 的待审行；落库规范全称或 `NULL`；找不到厂去 `#/supplier-list`，本页不建档。

列表抽屉继续给零星改。本页给采购按厂分包时一次改几百行。

---

## 1. 为什么单独一页

| 已有 | 不够 |
|------|------|
| 列表确认抽屉远程搜供应商 | 上万供应商不能塞进下拉；一件一件点选扛不住分包清单 |
| 列表「导出 Excel」 | 三表、合并单元格、水印、列很多；**不是**可导回的工作底稿 |
| 供应商切片上传 | 建档（缩写/全称/ERP/别名），**不是**给采购对象行指定对方 |

所以：侧栏「采购对象」分组里，生成 / 清单 **下面** 再开一页 **上传供应商**。前端目录：

```
static/js/features/bom/procurement-object/
  generate/
  list/
  supplier-upload/     ← 本页
```

Hash：`#/bom-procurement-object-supplier-upload`。  
面包屑：焊接工程 → 采购对象 → 上传供应商。

禁止把上传区塞进清单页底部（清单 HUD / 密表已经满）。禁止复用列表导出文件当模板。

---

## 2. 页面交互（写死）

对齐现网焊接单价 / 年度零件价上传壳：范围下拉 + 下载模板 + 拖拽区 + 同步导入。

1. 基地 / 项目 / 版本 **三键必选**。级联与生成页 **同一模块** `snapshot-cascade.js` → BOM 上级域 `GET /api/bom/filters/cascade?version_source=snapshot`；**禁止**在采购对象域另挂 cascade / 默认 L0（会露出 EC）。未选齐则按钮不可用。  
2. **下载模板**：`get_by_unique_key` → 无材料清单 → 「未找到对应材料清单」；有 snapshot 无采购对象头 → 「尚未生成采购对象清单」；有头但 `section=object` 为零 → 「没有可指定供应商的采购对象」。检测未通过 **仍允许**。模板按零件号去重抄库现况。  
3. 用户只改「供应商」列；可删掉不改的行（文件里没有的行 **不改库**）。  
4. **上传**：同一三键 + `.xlsx`。范围以 **表单** 为准。  
5. 成功 Toast：更新 / 清空 / 未变 条数。失败整单不写。

模板下载不经审核权限。无上传权则隐藏下载与提交，与现网上传页一致。

---

## 3. 模板（与导出分家）

`GET /api/bom/procurement-objects/supplier-template?location=&vehicle_model=&bom_version=`（三键必填，版本=snapshot 头）

**模板 = 该 snapshot 下采购对象清单按零件号去重后的库现况。** 取件：`get_by_unique_key` → `get_list_by_snapshot_id` → `section=object`。禁止 L0/EC 裁、禁止「全部版本」。

清单库仍按节点保留多行（同一零件号可挂在多个供货总成下）。**本页模板一行一个零件号**，导入按零件号写回该范围全部 `section=object` 行。核对区（标准件/胶等、异常）**不出**。先按供货总成零件号、零件号、`excel_row` 排对象行，再按零件号保留首次出现。

同一零件号若库里对方不一致，模板写出排序后第一条的供应商；再导入会把其余行改成同一对方。对方已全部相同则一行不改再导入计未变。

| 工作表 | 内容 | 导入 |
|--------|------|------|
| 第一页 `采购对象` | 清单行现况 | **唯一读取** |
| 第二页 | 把同一 `wb` 交给供应商导出；表名用现网导出原名（现为 `供应商`） | **不读**。对照用，可复制全称/缩写/ERP 填回第一页「供应商」列 |
| 第三页 `填写说明` | 短说明 | 不读 |

**下载写表顺序写死：**

1. 第一页 `采购对象`（占住默认空表，清单现况）。  
2. 把 `wb` 交给 `SupplierService.write_catalog_to_workbook`（现网导出往里加页，不改名）。  
3. 第三页 `填写说明`。

供应商导出必须改造：抽出「往已有 `Workbook` 写目录」；一览 `export_excel` 自己 `Workbook()` 再调同一方法后打水印。签名落在供应商切片，例如 `write_catalog_to_workbook(db, workbook, *, is_enabled=True)`（已启用全量、无关键字）。禁止 BOM 复制 `_new_import_sheet` / `_write_import_row`。禁止 `export_excel` 返回的 bytes 再 `load_workbook` 拼进来。

本页不知道、也不维护表页中文名：以供应商切片常量为准。切片以后若改导出表名，本模板跟着变，不要在 BOM 写死 `sheet.title = "供应商"`。

供应商主数据 **不按基地切**（[supplier-design.md](../masterdata/supplier-design.md) S1 / S2）。表单选基地只圈定采购对象清单；副页仍是全平台已启用行，无关键字、不分页。禁止按基地从工艺 / 采购对象 `DISTINCT` 一份假名单。禁用行不进副页（不能新指定）。

Parser **只读第一页**。改供应商目录页、在该页增行 **不会** 建档、也不会写入采购对象。建档仍只走 `#/supplier-list` / 供应商上传。

第一页冻结 `A2`。

| 列 | 模板写入 | 导入 |
|----|----------|------|
| 零件号 | `part_number`（去重键） | **对账键**。不属于本范围对象行 → 整单拒绝 |
| 零件名称 | `part_name`（该零件号排序后首次） | 忽略 |
| 内部号 | 本行节点 `internal_number`（给人看，到 ERP 联查；可空） | **忽略**，不参与对账 |
| 对象种类 | 中文（退化供货件 / 分总成 / 冲压件） | 忽略 |
| 确认 | 中文（待定 / 外发 / 自制） | **忽略，不改确认** |
| 审核 | 中文 | 忽略 |
| 供应商 | **抄库** `supplier_name`（规范全称，取该零件号排序后首次）；未指定 `NULL` → 空单元格。已指定必须带出，禁止模板里故意留空 | **唯一写入列**；写回该零件号全部对象行 |

文件名：`采购对象供应商_{location}_{vehicle_model}_{bom_version}.xlsx`。
空表（仅表头）仍出文件，但 Service 在「零对象行」时先拒单、不出空壳糊弄人。

同一零件号库里对方已全部相同：下载后的文件 **一行不改即可再导入**（全部计「未变」）。

禁止：把列表导出的 21 列、合并单元格、页眉水印当本模板；禁止模板里预填缩写（列上与库一致，写全称；导入时缩写/别名/ERP 仍可解析）；禁止模板按节点拆成多行让用户填两次。

表头字符串只定义在 Parser `HEADER_*`，builder 与解析共用，禁止页面硬编码另一套。

---

## 4. 对账与写入

范围锁定后，Excel 行唯一键是 **零件号**。清单库仍以 `source_node_id` 存行；本页不按节点对账。文件里一行供应商，写回该零件号在本范围的全部对象行。计数按 **清单行**（一个零件号命中两行则 `updated_count=2`）。

| Excel 行 | 行为 |
|----------|------|
| 不在文件里 | 库行不动 |
| 「供应商」与该行库规范全称相同（空对空也算） | 该清单行未变 |
| 「供应商」空白（库非空） | 该零件号下各行清空 → `NULL`（自制行清空也允许，结果仍是空） |
| 「供应商」非空 | `SupplierService.require_enabled`，落 **规范全称** 到该零件号下各行 |
| 同一文件两个相同「零件号」 | 整单拒绝 |
| 「零件号」不属于本范围 `section=object` | **跳过**，结果里写明行号与零件号；不拦整单 |

文件里一行要 **改值** 时，对该零件号下 **每一行** 再跑与单条同一套规则（见 §5）。已审且要变 → **跳过该行**；待审照常写。未变的已审行计未变。

整单一个事务。任一行失败（如自制非空、未登记供应商）→ 全部不写、不登记溯源。已审跳过不算失败。

---

## 5. 门禁（与单条同一套）

上传前：`get_by_unique_key` → 无材料清单拒；`get_list_by_snapshot_id` → 无采购对象头拒。

| 条件 | 下载模板 | 上传（该行要改值时） |
|------|----------|----------------------|
| 未选基地 / 项目 / 版本 | 拒绝 | 拒绝 |
| 未找到对应材料清单 | 拒绝 | 拒绝 |
| 尚未生成采购对象清单 | 拒绝 | 拒绝 |
| `qa_passed=false` | 允许 | **允许**（与确认相同；黄条仅展示） |
| `audit_status=approved` 且供应商要变 | — | **跳过该行不改**，不计失败；待审行照常写 |
| `section≠object` | 不出这些行 | 若文件里出现 → 拒绝 |
| `confirm_status=in_house` 且供应商非空 | 仍按库原样带出（自制行库里应为 `NULL`） | **整单拒绝**（自制禁止非空；本页 **不** 改确认、也不擅自清空自制以外的业务） |
| 未登记 / 已禁用 | — | `require_enabled` 失败 → 整单拒绝，深链 `#/supplier-list` |

不要求先外发再指定。待定 / 外发都可以写对方。本页 **不写** `confirm_status` / 审核字段。

禁用供应商：不准新指定；模板里已有的历史全称若未改，计未变，不跑门禁。

---

## 6. API / 分层

仍挂现网前缀 `/api/bom/procurement-objects`，不新开 Router。选项检索继续用已落地的 `GET /supplier-choices`（本页不需要下拉）。

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/supplier-template` | `op:bom-procurement-object-supplier-upload:view` | Query：基地+项目+snapshot 头版本。流式 xlsx |
| POST | `/supplier-upload` | `op:bom-procurement-object-supplier-upload:upload` | `multipart`：`file` + 同上三键 |

响应 `ApiResponse[BomProcurementObjectSupplierUploadResultVO]`：`updated_count` / `cleared_count` / `unchanged_count` / `skipped_count` / `skipped_details`。已审要变计入 `unchanged_count`；零件号不在范围计入跳过并写明行号与零件号。

同步导入，不走异步 worker。体量就是一份清单的对象行，对齐年度价上传。

```text
Router
  └── BomProcurementObjectService（门面，≤编排）
        ├── LocationService.require_enabled / 项目存在性
        ├── get_by_unique_key → get_list_by_snapshot_id（与生成页同钥）
        ├── Parser（纯函数，只读第一页）
        ├── 下载：① `采购对象` ② `wb` → 供应商导出 ③ `填写说明`
        ├── SupplierService.require_enabled（非空且相对库有变化）
        ├── Repository 按零件号更新该范围全部对象行的 supplier_name
        └── 成功路径：落盘 + file_trace.register_existing
```

禁止：Router 调 Parser / 供应商 Repository；本切片代建供应商；从年度价 / `material_mill` / 备注填对方。

代码落点（落地时）：

| 文件 | 职责 |
|------|------|
| `app/services/masterdata/supplier/service.py` | 改造导出：收 `Workbook`；`export_excel` 与本页共用写表。表名仍由本切片 `resolve_worksheet` 决定 |
| `app/parsers/bom/procurement_object_supplier_parser.py` | 表头唯一来源；行 → dataclass；只读第一页 |
| `app/services/bom/procurement_object/supplier_template.py` | 第一页 `采购对象` + 第三页 `填写说明`；中间把 `wb` 交给供应商 Service，禁止改副页名 |
| `app/services/bom/procurement_object/supplier_upload_service.py` | 校验、对账、事务、溯源 |
| `static/js/features/bom/procurement-object/supplier-upload/` | 页面 |

---

## 7. 权限与溯源

新菜单挂在 `menu:bom-procurement-object-group` **末尾**（生成、清单之下）：

| 码 | 用途 |
|----|------|
| `menu:bom-procurement-object-supplier-upload` | 侧栏 |
| `op:bom-procurement-object-supplier-upload:view` | 进页、下载模板 |
| `op:bom-procurement-object-supplier-upload:upload` | 提交 |

不复用 `op:bom-procurement-object-list:update`：清单确认与 Excel 批改分开授权。改 `catalog.json` 后跑 `python -X utf8 -m scripts.generate_perm_codes`。不要把树抄进 `permission-design.md` §7。

前端同时：`pageMeta`、`app.js` 注册、侧栏 `data-page`、按钮 `can('op:…')`。

文件溯源：本页是业务 Excel 上传且须落盘，**纳入**。`file_category = bom_procurement_object_supplier`，标签「采购对象供应商」。成功 `commit` 前 `register_existing`；失败回滚不登记。下载模板不是上传，不登记。`FILE_CATEGORY_LABELS` / `CATEGORY_VIEW_PERMISSIONS` 已挂本页 view（及清单 view）。

---

## 8. 做 / 不做

| 做 | 不做 |
|----|------|
| 独立上传页；三键=生成页同钥（snapshot）；`version_source=snapshot` | 清单页内嵌上传；L0/EC cascade；「全部版本」凑合；按树根浏览裁 |
| 模板抄库现况，已指定供应商必须带出 | 空白填报壳；下载时把已有对方抹空 |
| 把 `wb` 交给供应商导出写表；表名原样接收 | 在 BOM 复制 Excel；`load_workbook` 拼文件；`sheet.title` 改副页；按基地伪造名单；Parser 读副页 |
| 窄表只改供应商；对账零件号，写回该号全部对象行 | 用表 `id`；按节点拆行让用户填两次；改确认 / 审核 / 种类 |
| 整单事务；已审要变则跳过 | 已审改值 silently 当成功写入；已审要变整单拒绝 |
| `require_enabled`；空单元格清空 | 自由文本落库；本页建供应商；空串 `''` |
| 文件缺行 = 不改 | 文件缺行 = 把库里对方清掉 |
| 同步导入 + 溯源 | 异步任务；一件多家 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-19 | **级联与生成页合一：** 共用 `snapshot-cascade.js`；禁止第二套逻辑。 |
| 2026-09-19 | **简化：与生成页同一把钥匙。** 三键必选 → `get_by_unique_key` → `get_list_by_snapshot_id`；废止全部版本 / 清单头裁包 / L0 浏览。 |
| 2026-09-19 | 版本下拉只读 snapshot 头；禁止 L0/`EC-*`。 |
| 2026-09-19 | **范围对齐：** 基地+项目+版本；禁止用 EC 找清单头。 |
| 2026-09-19 | 零件号不在范围：跳过并写明行号与零件号，不拦整单。 |
| 2026-09-19 | 检测未通过不拦上传；已审要变跳过不改（计未变）。 |
| 2026-09-08 | 模板增加「内部号」列：给人看、导入不读。 |
| 2026-09-08 | 落地：独立上传页 + 窄表导回；供应商导出收 `Workbook`。 |
| 2026-09-08 | 初稿：清单范围 Excel 批改供应商；覆盖「禁止 Excel 导回」；与单条 S12 同一写门禁。 |
| 2026-09-08 | 锁死：下载模板即库现况，已有供应商全称必须带出。 |
| 2026-09-08 | 下载顺序写死：第一页 `采购对象` → `wb` 给供应商导出 → 第三页 `填写说明`。 |
