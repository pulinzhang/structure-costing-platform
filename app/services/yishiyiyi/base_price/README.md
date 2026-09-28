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
from app.services.yishiyiyi.base_price.service import SteelBasePriceService
from app.services.yishiyiyi.base_price.export.service import SteelBasePriceExportService
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
   `export/service.py` 负责查库与扁平行；`excel_exporter` 负责 openpyxl。样式变更不搅进查询。

4. **仍遵守项目分层**  
   子包是 Service 内部拆分。写库走 Repository；解析只由 importing 调 Parser；Router 不直接碰 Parser / Repository。

包名用 `importing/` 而非 `import/`：后者是 Python 关键字。

本切片无阶梯匹配子包（匹配在 `policy/match`）；基准价是单表主数据。

---

## 3. 目录结构

```text
app/services/yishiyiyi/base_price/
├── README.md
├── __init__.py                         # 只作包标记，不汇总导出
├── service.py                          # 薄门面：只委托
├── gate.py                             # 写入门禁：中标钢厂、参考规格、加工费、月度涨跌、宽度告警
├── crud/
│   ├── __init__.py
│   └── service.py                      # CRUD、批量删除、核价取数、统计
├── importing/
│   ├── __init__.py
│   ├── service.py                      # 归档 + 解析 + upsert
│   └── template_builder.py             # 导入模板
└── export/
    ├── __init__.py
    ├── service.py                      # 导出预览查询、调导出器
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

crud / importing 写之前调用 gate.py

SteelBasePriceExportService      （也可由 Router 直接调 .export）
        │
        ▼
repositories.yishiyiyi.base_price
parsers.yishiyiyi.base_price     （仅 importing 调用）
```

| 子包 | 负责 | 不负责 |
|------|------|--------|
| `crud/` | 分页、详情、增删改、批量删、筛选项、`list_for_calc`、条件 count | 导入、xlsx 字节 |
| `gate.py` | 写入前拒绝或告警 | 查库、落库 |
| `importing/` | 源文件归档、Parser、upsert、进度回调、导入模板 | HTTP、Excel 样式 |
| `export/` | 导出预览扁平行、生成 xlsx | CRUD 写操作 |

门面可暴露 `service.repository`；优先走门面方法。

---

## 5. 关键业务约定

### 5.1 导入（`importing`）

- 整批 **单事务**：门禁拒绝则整批不写库。
- 加工费列必须存在，单元格必须是数字。不猜列、不填 120、不填 0。
- 牌号 / 钢种：`SteelGradeCategoryService.require_matched_grades`（内部 `match_by_grade_key`）命中后落档案 `grade` 与档案大类（Excel `DCO1`、档案 `DC01` → 存 `DC01`）。工艺导入同一入口。
- 基地必须是已启用的规范名。钢厂是自由文本，纯数字整批拒绝。
- Repository `upsert`：按表唯一键创建或更新。表唯一键是年、月、基地、钢厂、类别、牌号、厚度、宽度，比下面的中标门禁更宽，不要改成「一个月一个钢厂」。
- 导入前按年/月归档（`save_steel_price_upload`，`FILE_KIND_BASE_PRICE`），便于与政策文件成对核对。
- 进度通过 `ProgressCallback` 上报；进度写辅助库，不与本事务写锁耦合。

### 5.2 写入门禁（`gate.py`）

调用方先按年月取出行。两把钥匙不要和表唯一键混用。

| 钥匙 | 身份 | 结果 |
|------|------|------|
| 中标 `winning_mill_key` | 基地 + 牌号 | 同一个月只能有一个钢厂。同一钢厂、不同参考厚度可以。要换钢厂，先删掉原来那一条 |
| 月度涨跌 `month_move_key` | 基地 + 牌号 + 参考厚度 + 参考宽度 | 单价加加工费相对上月超出「基准价月度价格变动范围」则整批拒绝。等于该范围可以写入。钢厂优先对同一家；上月这一规格只有一条时，钢厂换了也对照那一条。对不上就不猜，本条放行 |

另外三条：

- 参考厚度、参考宽度为空则整批拒绝。厚度大于设置里的「车身件料厚上限」则整批拒绝，等于上限可以写入。默认 3.00 mm。
- 加工费大于设置里的「基准价加工费上限」则整批拒绝，等于上限可以写入。默认 120 元/吨。设置页填写时不能超过 300。
- 冷轧、酸洗常见宽度 1250 mm，镀锌常见 1250 和 1500 mm。其它宽度只告警，仍然写入。宽度不参与定价。

手工改单价或加工费走同一套月度涨跌和加工费上限。

### 5.3 导出（`export`）

- `list_for_export`：前端预览分页。  
- `export`：查全量筛选结果后交给 `SteelBasePriceExporter` 写工作簿。

### 5.4 核价取数（`crud`）

- `list_for_calc`：返回 ORM 列表（含 id），供 `costing/steel_price` 联动计算溯源，不做 VO 转换。

---

## 6. 职责

| 模块 | 职责 |
|------|------|
| `gate.py` | 中标、参考规格、加工费上限、月度涨跌、宽度告警 |
| `crud/service.py` | 列表字段 / 写操作审计；改价前调门禁 |
| `importing/service.py` | 导入 upsert 策略、进度分段；写入前调门禁 |
| `importing/template_builder.py` | 导入模板与填写说明 |
| `export/service.py` | 导出预览字段 |
| `export/excel_exporter.py` | Excel 列与样式 |

约束：门面不堆业务逻辑；Router 不直接调 Parser；子包之间避免成环。

---

## 7. 相关路径

| 层级 | 路径 |
|------|------|
| Router | `app/routers/yishiyiyi/base_price.py` |
| Service（本目录） | `app/services/yishiyiyi/base_price/` |
| Repository | `app/repositories/yishiyiyi/base_price/` |
| Parser | `app/parsers/yishiyiyi/base_price/` |
| DTO / VO | `app/schemas/dto/steel_base_price_dto.py`、`app/schemas/vo/steel_base_price_vo.py` |
| 前端 | `static/js/features/yishiyiyi/base-price/` |
| API 前缀 | `/api/yishiyiyi/base-price` |
| 对照结构 | `app/services/yishiyiyi/policy/`、`app/services/costing/stamping_part_cost/` |
