# 钢材基准价格 Service（`yishiyiyi/base_price`）

> 一事一议 · 钢材基准价格业务层  
> 路径：`app/services/yishiyiyi/base_price/`

采用「根门面 + 按关注点子包」组织，与 `yishiyiyi/policy`、`costing/stamping_part_cost` 一致。

---

## 1. 业务范围

承接「钢材基准价格」业务逻辑，供 Router 与核价联动使用：

| 能力 | 说明 |
|------|------|
| 主表 CRUD | 列表、详情、增删改、按年/月等条件批量删除 |
| Excel 导入 | 归档 → 解析 → 事务内 upsert |
| 导出预览 / 下载 | 扁平行分页预览；生成 xlsx |
| 核价取数 | 按年/月/基地列出 ORM，供钢材联动计算 |

**对外入口**：

```python
from app.services.yishiyiyi.base_price import (
    SteelBasePriceService,
    SteelBasePriceExportService,
)
```

- `SteelBasePriceService`：CRUD / 导入 / 导出预览 / 核价取数（门面）  
- `SteelBasePriceExportService`：生成 Excel 文件（Router 下载接口直接使用）

业务调用优先经上述入口；子包实现类供本切片内部使用。

---

## 2. 为什么这样组织

1. **按关注点分包**  
   CRUD、导入、导出变更动机不同：导入看 `importing/`，表格样式看 `export/excel_exporter.py`。

2. **门面只做委托**  
   `SteelBasePriceService` 不写业务细节，只转发。对外能力在门面，细节在子包。

3. **查询组装与 Excel 生成分离（导出）**  
   `export_service` 负责查库与扁平行；`excel_exporter` 负责 openpyxl。样式变更不搅进查询。

4. **仍遵守项目分层**  
   子包是 Service 内部拆分。写库走 Repository；解析只由 importing 调 Parser；Router 不直接碰 Parser / Repository。

包名用 `importing/` 而非 `import/`：后者是 Python 关键字。

本切片无阶梯匹配子包（匹配在 `policy/match`）；基准价是单表主数据。

---

## 3. 目录结构

```text
app/services/yishiyiyi/base_price/
├── README.md
├── __init__.py                         # re-export Service / ExportService
├── steel_base_price_service.py         # 薄门面：只委托
├── crud/
│   ├── __init__.py
│   └── base_price_crud.py              # CRUD、批量删除、核价取数、统计
├── importing/
│   ├── __init__.py
│   └── import_service.py               # 归档 + 解析 + upsert
└── export/
    ├── __init__.py
    ├── export_service.py               # 导出预览查询、调导出器
    └── excel_exporter.py               # openpyxl 生成
```

---

## 4. 依赖方向

```text
Router / 钢材联动计算 / Dashboard
        │
        ▼
SteelBasePriceService            （门面）
   ├── crud.SteelBasePriceCrudService
   ├── importing.SteelBasePriceImportService
   └── export.SteelBasePriceExportService
             └── SteelBasePriceExporter

SteelBasePriceExportService      （也可由 Router 直接调 .export）
        │
        ▼
repositories.yishiyiyi.base_price
parsers.yishiyiyi.base_price     （仅 importing 调用）
```

| 子包 | 负责 | 不负责 |
|------|------|--------|
| `crud/` | 分页、详情、增删改、批量删、筛选项、`list_for_calc`、条件 count | 导入、xlsx 字节 |
| `importing/` | 源文件归档、Parser、upsert、进度回调 | HTTP、Excel 样式 |
| `export/` | 导出预览扁平行、生成 xlsx | CRUD 写操作 |

门面可暴露 `service.repository`；优先走门面方法。

---

## 5. 关键业务约定

### 5.1 导入（`importing`）

- 整批 **单事务**：失败全回滚。
- 牌号 / 钢种：`SteelGradeCategoryService.require_matched_grades`（内部 `match_by_grade_key`）命中后落档案 `grade` 与档案大类（Excel `DCO1`、档案 `DC01` → 存 `DC01`）。工艺导入同一入口。
- Repository `upsert`：按业务唯一键创建或更新。
- 导入前按年/月归档（`save_steel_price_upload`，`FILE_KIND_BASE_PRICE`），便于与政策文件成对核对。
- 进度通过 `ProgressCallback` 上报；进度写辅助库，不与本事务写锁耦合。

### 5.2 导出（`export`）

- `list_for_export`：前端预览分页。  
- `export`：查全量筛选结果后交给 `SteelBasePriceExporter` 写工作簿。

### 5.3 核价取数（`crud`）

- `list_for_calc`：返回 ORM 列表（含 id），供 `costing/steel_price` 联动计算溯源，不做 VO 转换。

---

## 6. 扩展时改哪里

| 需求 | 落点 |
|------|------|
| 列表字段 / 写操作审计 | `crud/base_price_crud.py` |
| 导入 upsert 策略或进度分段 | `importing/import_service.py` |
| 导出预览字段 | `export/export_service.py` |
| Excel 列或样式 | `export/excel_exporter.py` |
| 新增对外能力 | 先在对应子服务实现，再在门面（或 `__init__`）暴露 |

约束：

- 门面不堆业务逻辑  
- Router 不直接调 Parser  
- 子包之间避免互相调用成环

---

## 7. 相关路径

| 层级 | 路径 |
|------|------|
| Router | `app/routers/yishiyiyi/base_price/` |
| Service（本目录） | `app/services/yishiyiyi/base_price/` |
| Repository | `app/repositories/yishiyiyi/base_price/` |
| Parser | `app/parsers/yishiyiyi/base_price/` |
| DTO / VO | `app/schemas/dto/steel_base_price_dto.py`、`app/schemas/vo/steel_base_price_vo.py` |
| 前端 | `static/js/features/yishiyiyi/base-price/` |
| API 前缀 | `/api/yishiyiyi/base-price` |
| 对照结构 | `app/services/yishiyiyi/policy/`、`app/services/costing/stamping_part_cost/` |
