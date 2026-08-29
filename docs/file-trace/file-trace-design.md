# 文件溯源 — 设计说明

> 状态：**已上线（MVP）**  
> 历史：侧栏「报价」占位页（`#/quotation`）已替换为 **文件溯源**（`#/file-trace`）；quotation 代码与权限码已移除。  
> 关联：`docs/architecture.md`、`docs/permission-design.md`、`docs/api-type-safety.md`  
> 现网：`app/routers/file_trace/`、`app/services/file_trace/`、`static/js/features/file-trace/`、`tests/file_trace/test_register.py`

---

## 0. 范围边界（硬约束）

**只与业务有关的 Excel 上传、且后端已把原件保存到磁盘，才做文件溯源。** 其它一律不做。

**纳入须同时满足三条（缺一不可）：**

1. **业务 Excel 上传**：用户通过业务 import/upload 接口提交 `.xlsx` / `.xls`（非头像、非模板下载、非系统导出）；
2. **原件已落盘**：对应 Service 在 import 流程中 **已将同一 Excel 写入 `UPLOAD_DIR`**（可核对：代码中存在 `save_*_upload` / `_save_excel_file` / `_save_file` 写 Excel，而非仅 `parse_*_excel` 入库）；
3. **成功路径登记**：业务事务提交前调用 `register_existing`；失败/回滚 **不登记**。

| 判定 | 说明 |
|------|------|
| **不纳入** | **无 Excel import**（废料销售价 CRUD） |
| **不纳入** | **非上传**（冲压加工费、焊接工艺拆解、L0 焊接费等计算/生成；焊接拆解导出 Excel 属导出，非上传原件） |
| **不纳入** | 简图 PNG、用户头像、报价单 |

**本期纳入的后端（现网已落盘）：**

| `file_category` | 登记触发 Service / 工具 |
|-----------------|-------------------------|
| `bom_material` | `BomUploadService.import_excel` |
| `stamping_process` | `StampingUploadService.process_upload` |
| `stamping_die` | `StampingDieUploadService.process_upload` |
| `stamping_gauge_fee` | `StampingGaugeFeeUploadService.import_excel` |
| `stamping_tonnage_price` | `StampingTonnagePriceImportService` + `save_tonnage_price_upload` |
| `steel_base_price` | `SteelBasePriceImportService` + `save_steel_price_upload` |
| `steel_price_policy` | `SteelPricePolicyImportService` + `save_steel_price_upload` |
| `bom_packaging_transport_fee` | `BomPackagingTransportFeeImportService` + `save_packaging_transport_fee_upload` |
| `bom_welding_unit_price` | `BomWeldingUnitPriceImportService` + `save_welding_unit_price_upload` |
| `bom_annual_part_price` | `BomAnnualPartPriceImportService` + `save_annual_part_price_upload` |

**现网全量对照（Excel 相关）：**

| 模块 | 有 Excel import | Excel 落盘 | 溯源 |
|------|-----------------|------------|------|
| BOM 材料清单 | ✅ | ✅ | ✅ |
| 冲压工艺 | ✅ | ✅ | ✅ |
| 冲压模具布点 | ✅ | ✅ | ✅ |
| 冲压检具费 | ✅ | ✅ | ✅ |
| 冲次单价 | ✅ | ✅ | ✅ |
| 钢价基准价 | ✅ | ✅ | ✅ |
| 钢价加减价政策 | ✅ | ✅ | ✅ |
| 包装运输费 | ✅ | ✅ | ✅ |
| 焊接单价 | ✅ | ✅ | ✅ |
| 年度零件价 | ✅ | ✅ | ✅ |
| 废料销售价 | ❌ | — | ❌ |
| 冲压加工费 / 焊接工艺拆解 / L0 焊接费等 | ❌ | — | ❌ |

某模块 **未来** 若新增原件落盘，再单独开需求：先改该模块 upload Service 落盘，再加 `file_category` 与登记钩子。

---

## 1. 背景与问题

### 1.1 用户诉求

采购 / 核价 / 工艺同事需要在一个入口：

- **按业务分类**浏览历史上传的 Excel；
- **下载原件**，核对「当时导入的是不是这份表」；
- **查看元数据**（谁上传、何时、对应哪期基地/车型/年月）。

深链到业务列表为可选增强，**不在本期必做**。

### 1.2 现状（纳入范围的已落盘类）

| 上传场景 | 磁盘落盘 | 库内可追溯字段 | 问题 |
|----------|----------|----------------|------|
| BOM 材料清单 | `uploads/bom/…` | `bom_snapshots.source_filename / path / hash` | 较完整，但只在 BOM 切片 |
| 冲压工艺 | `uploads/{基地}/{车型}/{版本}/` | 零件表 `excel_filename`，**无统一 path** | 路径散落，无中央索引 |
| 冲次单价 | `uploads/stamping/tonnage-price/{年}/{基地}/` | 无行级 path | 已归档并登记 |
| 焊接单价 | `uploads/bom/welding-unit-price/{年}/{基地}/` | 无行级 path | 已归档并登记 |
| 年度零件价 | `uploads/bom/annual-part-price/{年}/{基地}/` | 无行级 path | 已归档并登记 |
| 钢价基准价 / 政策 | `uploads/steel-price/{年}/{月}/` | 行级 `excel_filename`，**无 path** | 归档与业务表未关联 |
| 包装运输费 | `uploads/bom/packaging-transport-fee/…` | 表内有 `excel_filename` | 有归档工具，无统一列表 |

此外，`main.py` 将 **`/uploads` 静态挂载为无鉴权目录**——知道 URL 即可下载。溯源应走 **鉴权下载 API**（见 §8）。

### 1.3 设计结论

> **`upload_files` 注册表是溯源列表的单一真相**；**仅**上述已落盘 upload Service 在落盘成功且业务事务提交前调用 `register_existing`；历史数据通过 **定向回填** 补齐，遵守 supersede 规则。

不复用「报价」域模型；报价若未来落地，应作为独立切片，与溯源无关。

---

## 2. 产品范围

### 2.1 一句话

> **已落盘业务 Excel 的登记中心：分类筛选、元数据查看、鉴权下载。**

### 2.2 本期做（MVP）

| 能力 | 说明 |
|------|------|
| 列表 | 分页 HUD 密表；分类、基地、年度、月份、车型、上传人、时间范围、文件名模糊 |
| 下载 | `HttpClient.download` 走 `/api/file-trace/{id}/download` |
| 详情抽屉 | 分类、原名、scope、SHA256、大小、上传人、时间 + 下载 |
| 分类 Tab / 筛选 | 仅 §0 所列 `file_category` |
| 权限 | `menu:file-trace` + `op:file-trace:view` + 与业务分类取交集（见 §7） |
| 空状态 UX | 无可见分类时提示「当前账号无可溯源分类」，非空白表 |

### 2.3 本期不做（非目标）

| 非目标 | 原因 |
|--------|------|
| 无 Excel import / 非上传原件（废料价、加工费、焊接拆解等） | 非上传原件场景 |
| 废料价、加工费、焊接拆解、头像、报价 | 非上传原件场景 |
| 在线 Excel 预览 | 下载 + 元数据即可 |
| 通用网盘 / 用户自建上传 | 不是网盘产品 |
| 替换各业务页「导入模板下载」 | 仍走各模块 template API |
| 删除 / 物理覆盖原件 | 防扯皮；仅 `superseded` 标记 |
| 简图 PNG | 非 Excel 上传原件 |
| 全目录扫描回填 | 易误分类；只做定向回填（§6.2） |
| 业务页深链 | 可选后续；scope 字段已够用 |

### 2.4 「查看」的定义

| 文件类型 | 行为 |
|----------|------|
| `.xlsx` / `.xls` | 详情抽屉 + **下载** |

---

## 3. 信息架构与导航

### 3.1 侧栏

将 `static/index.html` 原「报价」改为「文件溯源」（**已完成**）：

```text
文件溯源  →  #/file-trace
data-page="file-trace"
```

`#/quotation`、`menu:quotation`、`op:quotation:view` 已移除。

### 3.2 路由与前端模块

```text
static/js/features/file-trace/
  template.js   # 筛选 HUD + HUD 密表 + 详情抽屉
  index.js      # pageConfig
```

`app.js` 注册 `file-trace`；`features/index.js` 增加 `pageMeta`：

| 字段 | 值 |
|------|-----|
| `title` | 文件溯源 |
| `en` | `FILE_TRACE` |
| `breadcrumb` | `['文件溯源']` |

### 3.3 页面布局（对齐 `front-end.mdc` §4.4 HUD 密表）

```text
┌─ 筛选 HUD ─────────────────────────────────────────┐
│ 分类 ▾  基地 ▾  年度 ▾  月份 ▾  车型 ▾  上传人 ▾     │
│ 文件名搜索 [____________]  上传时间 [起]—[止]  [查询] │
└────────────────────────────────────────────────────┘
┌─ 列表（分类徽章 | 原件名 | scope | 大小 | 上传人 | 时间 | 操作）┐
│  … 仅操作列：详情、下载（禁止整行点击）                            │
└──────────────────────────────────────────────────────────────────┘
┌─ 分页 ───────────────────────────────────────────────────────────┘

无可见分类时：居中说明「暂无权限范围内的文件分类，请联系管理员授权业务菜单」。

详情抽屉（z-[85]）：
  - 分类、原始文件名
  - scope：基地 / 年度 / 月份 / 车型 / bom_version / process_version / 供应商
  - SHA256、字节大小、扩展名
  - 上传人、上传时间
  - [下载原件]
```

强调色：页内统一 `#FF1E27` 或 `#d32f2f` 二选一。

---

## 4. 领域模型

### 4.1 切片定位（基础设施横切）

`file_trace` 与 `async_task`、操作日志同类：**基础设施横切切片**，不是业务下游编排。

```text
app/models/file_trace/upload_file.py
app/repositories/file_trace/upload_file_repository.py
app/services/file_trace/upload_file_service.py
app/services/file_trace/register.py          # 供各 upload Service 调用
app/routers/file_trace/crud.py
app/schemas/dto/file_trace_dto.py
app/schemas/vo/file_trace_vo.py
```

依赖方向：

```text
已落盘 upload Service → file_trace.register_existing（写登记）
file_trace Service → upload_file Repository（读列表 / 下载）
```

| 允许 | 禁止 |
|------|------|
| 上述 upload Service 调用 `register_existing` | `file_trace` 依赖 `costing`（下游） |
| `register` 内路径校验、hash 计算 | `file_trace` Service 依赖业务 Repository 补全展示名 |
| 回填脚本读 `bom_snapshots`、已知 archive 路径（离线） | Router 直接登记；为未落盘模块预留枚举 |

列表展示名用 **scope 字段拼接**（如「BOM · 青岛 · T28 · D_00」）。`business_ref_type` / `business_ref_id` 可选存储（BOM 写 `bom_snapshot`），**不做**详情深链 UI。

### 4.2 文件分类 `file_category`

| `file_category` | 中文 | scope 字段 | 登记触发点 |
|-----------------|------|------------|------------|
| `bom_material` | BOM 材料清单 | `location`, `vehicle_model`, `bom_version` | `BomUploadService.import_excel` |
| `stamping_process` | 冲压工艺 | `location`, `vehicle_model`, `process_version`, `stamping_supplier` | `StampingUploadService.process_upload` |
| `stamping_die` | 冲压模具布点 | `location`, `vehicle_model` | `StampingDieUploadService.process_upload` |
| `stamping_gauge_fee` | 冲压检具费 | `location`, `vehicle_model` | `StampingGaugeFeeUploadService.import_excel` |
| `stamping_tonnage_price` | 冲次单价 | `location`, `year` | 冲次单价 import（归档后登记） |
| `steel_base_price` | 钢价基准价 | `year`, `month` | 基准价 import（归档后登记） |
| `steel_price_policy` | 加减价政策 | `year`, `month` | 政策 import（归档后登记） |
| `bom_packaging_transport_fee` | 包装运输费 | `location`, `year`, `vehicle_model` | 包装运输费 import（归档后登记） |
| `bom_welding_unit_price` | 焊接单价 | `location`, `year` | 焊接单价 import（归档后登记） |
| `bom_annual_part_price` | 年度零件价 | `location`, `year` | 年度零件价 import（归档后登记） |

字段命名：

- **`bom_version`**：仅 BOM（对齐 `bom_snapshots.bom_version`）。
- **`process_version`**：冲压工艺版本（对齐冲压 `version`，不与 BOM 混用）。

**不定义** `other`、预留空分类或「未来 Phase 2」枚举值。

### 4.3 与 `bom_snapshots` 的关系（双写策略）

**定稿：采用策略 A。**

| 策略 | 说明 |
|------|------|
| **A** | `upload_files` 为 **溯源列表唯一真相**；`bom_snapshots` 保留 `source_filename / source_file_path / source_file_hash` 作 BOM 切片内冗余。`BomUploadService` 在同一事务内：`register_existing` + 写 snapshot 字段（值一致）。 |
| B（远期可选） | snapshot 仅存 `upload_file_id`。 |

禁止：列表读 snapshot、下载走另一路径，与 `upload_files` 多套真相并存。

### 4.4 表结构：`upload_files`

模型继承 **`AuditUserMixin`**；`created_by` / `updated_by` 存 **用户名**。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | PK | |
| `file_category` | String(40) | §4.2 枚举，索引 |
| `original_filename` | String(255) | 用户上传时的文件名 |
| `stored_relpath` | String(500) | **相对 `UPLOAD_DIR`**，UNIQUE |
| `file_hash` | String(64) | SHA256 hex |
| `file_size` | Integer | 字节 |
| `extension` | String(20) | 小写，如 `.xlsx` |
| `location` | String(100) | 可空 |
| `year` | Integer | 可空 |
| `month` | Integer | 可空，1–12 |
| `vehicle_model` | String(100) | 可空 |
| `bom_version` | String(100) | 可空；仅 BOM |
| `process_version` | String(100) | 可空；仅冲压 |
| `stamping_supplier` | String(100) | 可空；冲压 |
| `business_ref_type` | String(40) | 可空，如 `bom_snapshot` |
| `business_ref_id` | Integer | 可空 |
| `status` | String(20) | `active` / `superseded` / `missing` |
| `superseded_by_id` | FK self | 同 scope 新上传替代时指向新记录 |
| + AuditUserMixin | | `created_at`, `created_by`, `updated_at`, `updated_by` |

索引建议：

- `(file_category, created_at DESC)`
- `(location, year, month)`
- `(vehicle_model, bom_version)` / `(vehicle_model, process_version)`
- `stored_relpath` UNIQUE

### 4.5 Supersede 规则

同一 **supersede 组** 内仅一条 `status=active`。再次上传成功 → 旧 `active` 改 `superseded`，并设 `superseded_by_id`。

| `file_category` | supersede 匹配键（非空字段 AND） |
|-----------------|----------------------------------|
| `bom_material` | `file_category` + `location` + `vehicle_model` + `bom_version` |
| `stamping_process` | `file_category` + `location` + `vehicle_model` + `process_version` + `stamping_supplier` |
| `stamping_die` | `file_category` + `location` + `vehicle_model` |
| `stamping_gauge_fee` | `file_category` + `location` + `vehicle_model` |
| `stamping_tonnage_price` | `file_category` + `location` + `year` |
| `steel_base_price` | `file_category` + `year` + `month` |
| `steel_price_policy` | `file_category` + `year` + `month` |
| `bom_packaging_transport_fee` | `file_category` + `year` + `location` + `vehicle_model` |
| `bom_welding_unit_price` | `file_category` + `location` + `year` |
| `bom_annual_part_price` | `file_category` + `location` + `year` |

列表默认 `status=active`。

### 4.6 登记 API（内部，非 HTTP）

**本期只实现 `register_existing`**——已落盘模块均先落盘再入库，无需 `save_and_register`。

```python
# app/services/file_trace/register.py

def register_existing(
    db: Session,
    *,
    file_category: str,            # 必须是 §4.2 枚举之一
    stored_relpath: str,             # 相对 UPLOAD_DIR；调用方已落盘
    original_filename: str,
    current_user: UserVO,
    file_hash: str | None = None,    # 未传则从磁盘计算 SHA256
    location: str | None = None,
    year: int | None = None,
    month: int | None = None,
    vehicle_model: str | None = None,
    bom_version: str | None = None,
    process_version: str | None = None,
    stamping_supplier: str | None = None,
    business_ref_type: str | None = None,
    business_ref_id: int | None = None,
    supersede_same_scope: bool = True,
) -> UploadFile:
    """登记已落盘原件。仅允许 §0 所列 upload Service 调用。"""
```

规则：

1. `stored_relpath` 经 `resolve()` 校验，必须在 `UPLOAD_DIR` 下，禁止 `..`；提供 `to_upload_relpath(absolute_path)` 统一转换；
2. `extension` 来自 `original_filename`；`file_size` / `file_hash` 以磁盘为准；
3. **与上游业务同一 SQL 事务**：业务写入成功之后、`commit` 之前调用；失败则整体回滚（磁盘孤儿文件可不登记，与现网一致）；
4. `supersede_same_scope=True` 时按 §4.5 处理；
5. 钢价 import **解析无有效行但已归档**时仍登记（证明「确实传过该文件」）；
6. 返回 ORM `UploadFile`，不返回 API VO。

各 upload Service **只调用此函数**，不在 Router 登记。

---

## 5. HTTP API

前缀：`/api/file-trace`  
JSON 端点使用 `response_model=ApiResponse[T]`；**下载为 `StreamingResponse` 例外**。

| 方法 | 路径 | 说明 | 响应 |
|------|------|------|------|
| GET | `/list` | 分页列表 | `ApiResponse[PageResult[UploadFileVO]]` |
| GET | `/filters` | 筛选项（**仅用户可见分类**） | `ApiResponse[UploadFileFiltersVO]` |
| GET | `/{id}` | 单条详情 | `ApiResponse[UploadFileVO]`（与列表同 VO） |
| GET | `/{id}/download` | 鉴权下载原件 | `StreamingResponse` |

### 5.1 列表查询参数 `UploadFileListQuery`

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` / `size` | int | 分页（`page` 从 1 起） |
| `file_category` | str? | 须在 `allowed_categories` 内 |
| `location` | str? | |
| `year` | int? | |
| `month` | int? | |
| `vehicle_model` | str? | 模糊 |
| `filename` | str? | 匹配 `original_filename` |
| `created_by` | str? | 上传人（用户名） |
| `uploaded_from` / `uploaded_to` | date? | 基于 `created_at` |
| `status` | str? | 默认 `active` |

### 5.2 `UploadFileVO`

`id`, `file_category`, `file_category_label`, `original_filename`, `file_size`, `file_size_text`, `extension`, `location`, `year`, `month`, `vehicle_model`, `bom_version`, `process_version`, `stamping_supplier`, `file_hash`, `status`, `created_at`, `created_by`。

### 5.3 下载接口

- Router：`Depends(require_perm(Perm.FILE_TRACE_DOWNLOAD))`；
- Service：记录属于 `allowed_categories`；`status` 为 `active` 或 `superseded`；磁盘存在；
- `Content-Disposition: attachment; filename*=UTF-8''{original_filename}`；
- 操作日志：`op:file-trace:download`。

**禁止** 在 VO 中返回 `/uploads/…` 直链 URL。

---

## 6. 改造点（已落盘 upload Service）

| 模块 | 改造 |
|------|------|
| `BomUploadService` | 事务内 `register_existing` + snapshot 冗余字段（§4.3）；`business_ref_type=bom_snapshot` |
| `StampingUploadService` | `db.begin()` 内、`commit` 前 `register_existing`（相对路径） |
| `StampingTonnagePriceImportService` | archive 后、事务 `commit` 前 `register_existing` |
| `BomWeldingUnitPriceImportService` | archive 后、事务 `commit` 前 `register_existing` |
| `BomAnnualPartPriceImportService` | archive 后、事务 `commit` 前 `register_existing` |
| `SteelBasePriceImportService` | 归档后、事务 `commit` 前 `register_existing`（含「无有效行」早退路径） |
| `SteelPricePolicyImportService` | 同上（含异步后台线程路径 §6.2） |
| `BomPackagingTransportFeeImportService` | archive 后、事务 `commit` 前 `register_existing` |

### 6.1 异步上传（钢价基准价、钢价政策）

二者均为 Router 收文件 → 后台线程 import；登记规则相同：

| 规则 | 说明 |
|------|------|
| 登记点 | 后台线程内 `import_excel` / `import_from_parser` 的 **同一事务**，`commit` 前 |
| 禁止 | Router 收到 `UploadFile` 时登记 |
| 失败 | 事务回滚则不登记；磁盘孤儿文件可不删（与现网一致） |

### 6.2 历史回填

脚本 `scripts/backfill_upload_files.py`，**仅定向来源**：

1. `bom_snapshots.source_file_path` → `bom_material`；
2. `uploads/steel-price/{year}/{month}/` → 按文件名 `_base-price_` / `_policy_` 区分；
3. `uploads/bom/packaging-transport-fee/` → `bom_packaging_transport_fee`；
4. `uploads/bom/welding-unit-price/` → `bom_welding_unit_price`（scope：年 + 基地）；
5. `uploads/bom/annual-part-price/` → `bom_annual_part_price`（scope：年 + 基地）；
6. `uploads/stamping/tonnage-price/` → `stamping_tonnage_price`（scope：年 + 基地）；
7. 冲压：`uploads/{基地}/{车型}/{版本}/` 下 `*.xlsx`（跳过同目录 `*.png`，跳过顶层 `stamping/`）→ `stamping_process`（scope 从路径段解析）。

规则：幂等（`stored_relpath` 已存在则跳过）；磁盘不存在 → `status=missing`；同 supersede 组仅最新一条 `active`。

**禁止** 扫描整个 `uploads/` 或写入 `other` 分类。

---

## 7. 权限设计

权限码已写入 `catalog.json`（quotation 相关码已删除）：

| 码 | 说明 |
|----|------|
| `menu:file-trace` | 侧栏「文件溯源」 |
| `op:file-trace:view` | 列表 / 详情 / filters |
| `op:file-trace:download` | 下载原件 |

### 7.1 与业务权限的交集

```text
1. menu:file-trace          → 侧栏可见
2. op:file-trace:view       → 可调列表 API
3. allowed_categories       → 由业务 view 权限推导（下表）
```

无 `allowed_categories` → 前端空状态说明，API 返回 `items=[]`（非 403）。  
`is_admin` → 全部分类开放。

### 7.2 `file_category` → 业务 view 权限

| `file_category` | 可见所需权限（任一） |
|-----------------|----------------------|
| `stamping_process` | `op:stamping-upload:view`, `op:stamping-parts:view` |
| `stamping_die` | `op:stamping-die-upload:view`, `op:stamping-die-list:view` |
| `stamping_gauge_fee` | `op:stamping-gauge-fee-upload:view`, `op:stamping-gauge-fee:view` |
| `stamping_tonnage_price` | `op:stamping-tonnage-upload:view`, `op:stamping-tonnage:view` |
| `steel_base_price` | `op:base-price-upload:view`, `op:base-price-download:view` |
| `steel_price_policy` | `op:steel-price-policy-upload:view`, `op:steel-price-policy-download:view` |
| `bom_material` | `op:bom-upload:view`, `op:bom-material:view` |
| `bom_packaging_transport_fee` | `op:bom-packaging-transport-fee-upload:view`, `op:bom-packaging-transport-fee:view` |
| `bom_welding_unit_price` | `op:bom-welding-unit-price-upload:view`, `op:bom-welding-unit-price:view` |
| `bom_annual_part_price` | `op:bom-annual-part-price-upload:view`, `op:bom-annual-part-price:view` |

---

## 8. 安全与 `/uploads` 静态目录

| 阶段 | 措施 |
|------|------|
| 本期 | 溯源页仅 API 下载；前端不拼 `/uploads` 直链 |
| 后续（可选） | 收紧 Excel 直链；简图可继续静态 |

---

## 9. 实施清单（单期 MVP）

- [x] 表 `upload_files` + 切片 API + 前端 `file-trace` 页（替换 quotation）
- [x] 权限树 + `generate_perm_codes`（`menu:file-trace` / `op:file-trace:view` / `op:file-trace:download`）
- [x] `register_existing` + §4.5 supersede
- [x] 已落盘 upload Service 登记钩子（含钢价基准/政策异步 §6.1、冲次单价）
- [x] 定向回填脚本 §6.2（`scripts/backfill_upload_files.py`）
- [x] 鉴权下载 + 操作日志
- [x] `tests/file_trace/`（现有 `test_register.py`；下载鉴权矩阵仍可补）

**明确不在本清单（仍未做）：** `save_and_register`、深链、路径迁移、`superseded` 列表筛选、导出溯源 Excel。

---

## 10. 测试要点

| 类型 | 内容 |
|------|------|
| 单元 | supersede 键、路径校验、`allowed_categories` |
| API | 无业务 view → 空列表；未登录下载 401/403 |
| 集成 | BOM / 冲压 / 冲次单价 / 焊接单价 / 年度零件价 / 钢价 / 包装运输费上传 → 列表 → 下载 hash 一致 |
| 异步 | 政策 import 成功/失败与登记一致性 |
| 回填 | 定向来源幂等；同 scope 仅一条 `active` |
| 负向 | 废料价 CRUD / 加工费计算等 **不产生** `upload_files` 记录 |

---

## 11. 废弃与迁移（已完成）

| 项 | 处理 |
|----|------|
| `app/routers/quotation/` | 已删除（仓库中无此目录） |
| `static/js/features/quotation/` | 已删除；现网为 `file-trace` |
| `catalog.json` `menu:quotation` | 已移除；现码 `menu:file-trace` |
| `Perm.QUOTATION_*` | 已移除；现码 `Perm.FILE_TRACE_*` |

---

## 12. 验收标准

> **上述已落盘业务 Excel 上传后，能在「文件溯源」找到并下载原件（hash 一致）；无业务 view 权限的用户不可见对应分类。**

| 场景 | 通过 |
|------|------|
| BOM 上传 | 列表有记录，scope 正确，可下载；与 snapshot 冗余一致 |
| 冲次单价上传 | 列表有「冲次单价」记录，基地+年度 scope 正确，可下载 |
| 焊接单价上传 | 列表有「焊接单价」记录，基地+年度 scope 正确，可下载 |
| 年度零件价上传 | 列表有「年度零件价」记录，基地+年度 scope 正确，可下载 |
| 钢价政策（异步） | 任务完成后有登记；失败无登记 |
| 重复上传同 scope | 旧 `superseded`，新 `active` |
| 权限 | 仅有 file-trace 菜单、无 BOM view → 无 BOM 分类 |
| 回填 | 定向来源正确；同 scope 仅最新 `active` |
| 负向 | 废料价 CRUD / 加工费计算后列表 **无** 新记录 |
| 安全 | 未登录不能 API 下载 |

---

## 13. 规范索引

| 文档 | 用途 |
|------|------|
| `docs/architecture.md` | 分层与切片 |
| `docs/permission-design.md` | §0 新增功能清单 |
| `docs/api-type-safety.md` | `ApiResponse`；下载类 `StreamingResponse` 例外 |
| `.cursor/rules/front-end.mdc` | HUD 密表、操作列、抽屉 z-index |
