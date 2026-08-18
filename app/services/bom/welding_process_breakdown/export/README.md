# 焊接工艺拆解 · L0 核对 Excel 导出（`export/`）

> BOM 切片 · 人工核对用宽表导出  
> 路径：`app/services/bom/welding_process_breakdown/export/`

本包**只做输出**：按列表相同筛选条件取出 L0 节点，渲染为便于操作人员核对的 `.xlsx`。  
不负责拆解生成、审核流、明细编辑。

---

## 1. 业务范围

| 能力 | 说明 |
|------|------|
| L0 核对表导出 | 强制 `level=0`；主表列纵向合并，明细分行 |
| 与列表同源筛选 | 基地 / 顾客 / 项目 / 版本 / 零件号 / 工艺数精确匹配 |
| 核对焦点列 | 标准工艺 · 标准单位（红）；计费用量 · 计费单位（黄） |
| 不计费噪音列 | 不含顾客、核对备注、审核字段 |

**对外入口**（Router 只依赖此名）：

```python
from app.services.bom.welding_process_breakdown.export import (
    BomWeldingProcessBreakdownExportOrchestrator,
)
```

**HTTP**：`GET /api/bom/welding-process-breakdown/export`  
**权限**：`Perm.BOM_WELDING_PROCESS_BREAKDOWN_EXPORT`（`op:bom-welding-process-breakdown:export`）

---

## 2. 为什么这样组织

1. **编排与渲染分离**  
   `orchestrator` 只做「查库 → 调 builder → 组文件名」；改 Excel 版式不必碰 Repository。

2. **列 / 值 / 样式 / 工作簿四层**  
   - 改表头、列宽、说明文案 → `columns.py`（无 openpyxl）  
   - 改单元格取值规则（计费口径、标准单位回填）→ `values.py`  
   - 改色板字体 → `styles.py`  
   - 改合并、冻结、斑马纹、状态着色 → `workbook.py`

3. **与列表筛选对齐，但不复用列表 VO**  
   取数走 `BomWeldingProcessBreakdownRepository.list_l0_for_export`（joinedload lines），导出侧自行排版，避免列表 API 为 Excel 长胖。

4. **仍遵守项目分层**  
   Router → Orchestrator → Repository；`workbook` **禁止**访问 DB。

---

## 3. 目录结构

```text
export/
├── README.md                 # 本说明
├── __init__.py               # 对外导出 Orchestrator
├── orchestrator.py           # 编排：筛选取数 → 渲染 → 文件名
├── columns.py                # 列布局、行高、文案、列号派生
├── values.py                 # 单元格取值、筛选摘要、文件名
├── styles.py                 # SheetStyle / fill / font / tone
└── workbook.py               # L0CheckWorkbookBuilder（openpyxl）
```

| 文件 | 负责 | 不负责 |
|------|------|--------|
| `orchestrator.py` | Session、Repository、调用 builder、打日志 | 单元格样式细节 |
| `columns.py` | `HEADERS`、主表/明细列数、说明 `NOTE`、列宽 | 读库、写 Excel |
| `values.py` | 计费用量、标准工艺名/单位、文件名 | 颜色、合并格 |
| `styles.py` | 色板、字体、状态 tone 映射 | 业务口径 |
| `workbook.py` | 标题/双层表头/数据行/合并/冻结/筛选 | SQL |

---

## 4. 依赖方向

```text
Router (welding_process_breakdown.py)
  └── BomWeldingProcessBreakdownExportOrchestrator
        ├── BomWeldingProcessBreakdownRepository.list_l0_for_export
        ├── values.filter_summary / build_filename
        └── L0CheckWorkbookBuilder.build
              ├── columns.*
              ├── values.*（行内取值）
              └── styles.*
```

**禁止**：

- `workbook` / `styles` / `columns` import Repository  
- Router 直接调用 `L0CheckWorkbookBuilder` 或 Repository  
- 在 `values` 里写 openpyxl

---

## 5. 数据流

```text
筛选参数
  → Repository.list_l0_for_export（L0 + lines）
  → filter_summary（表头第 2 行摘要）
  → L0CheckWorkbookBuilder.build
       · 每个 L0 一个序号；多工艺行时主表列纵向合并
       · 无工艺行整行浅红（工艺数=0）
  → (xlsx bytes, 数据行数)
  → build_filename + 时间戳
  → Router StreamingResponse / 下载
```

---

## 6. 表结构约定（与操作人员核对相关）

### 6.1 行结构

- **第 1 行**：标题  
- **第 2 行**：筛选摘要 + `共 N 个 L0` + 导出时间  
- **第 3 行**：核对说明（计费口径 + 单位换算举例）  
- **第 4 行**：分组表头（零件信息 | 工艺明细·核对区）  
- **第 5 行**：列名；自第 6 行起为数据；冻结至 `F6`（序号～零件号）

### 6.2 主表列（1–9，多工艺时纵向合并）

序号 · 基地 · 项目 · 版本 · 零件号 · 零件名称 · 焊接原文 · 工艺数 · 解析状态  

### 6.3 明细列（10–21）

行号 · 原文工艺 · 命中片段 · **标准工艺** · **标准单位** ·  
过程量 · 单位 · 次要过程量 · 次要单位 · **计费用量** · **计费单位** · 映射状态  

### 6.4 关键业务口径

| 规则 | 说明 |
|------|------|
| 计费用量 | 有 `process_qty_secondary` 则用次要过程量及单位，否则用过程量 |
| 标准单位 | 优先落库 `standard_process_unit`；缺失时按标准工艺名查目录单位 |
| 面积类展示 | 历史行若未落标准名，导出侧按「电泳≤244H」显示（与拆解约定一致） |
| 未来核价 | 说明文案标明：过程量单位与标准单位之间将做系数换算后再乘单价（例：mm→CM ÷10） |
| 不含列 | 顾客、核对备注、审核人/时间等（降低噪音） |

---

## 7. 扩展时改哪里

| 需求 | 落点 |
|------|------|
| 增删列、改表头文案、列宽、行高 | `columns.py` |
| 计费口径、标准名/单位回填、文件名规则 | `values.py` |
| 颜色、字体、解析/映射状态配色 | `styles.py` |
| 合并主表、冻结窗格、斑马纹、空工艺高亮 | `workbook.py` |
| 筛选字段、取数范围、日志 | `orchestrator.py` + Repository `list_l0_for_export` |
| 权限 / HTTP 参数 | `app/routers/bom/welding_process_breakdown.py` |

改列时注意：`HEADERS` 变更后，`COL` / `STD_COLS` / `BILLING_COLS` 等由列名派生的集合会跟着变；`workbook` 里若有硬编码列语义，一并核对。

---

## 8. 相关路径

| 角色 | 路径 |
|------|------|
| Router | `app/routers/bom/welding_process_breakdown.py`（`/export`） |
| 取数 | `app/repositories/bom/welding_process_breakdown_repository.py` → `list_l0_for_export` |
| 标准工艺 / 目录单位 | `app/common/bom/welding_standard_process.py` |
| 明细落库字段 | `app/models/bom_welding_process_breakdown.py`（含 `standard_process_unit`） |
| 前端下载 | `static/js/features/bom/welding-process-breakdown/list/` |
| 权限码 | `Perm.BOM_WELDING_PROCESS_BREAKDOWN_EXPORT` |

---

## 9. 本地冒烟（可选）

```powershell
python -X utf8 -c "from app.database import DatabaseConfig; from app.services.bom.welding_process_breakdown.export import BomWeldingProcessBreakdownExportOrchestrator; from app.repositories.bom.welding_process_breakdown_repository import BomWeldingProcessBreakdownRepository; db=DatabaseConfig.get_session_factory()(); n=BomWeldingProcessBreakdownRepository().list_l0_for_export(db)[0]; data,name=BomWeldingProcessBreakdownExportOrchestrator().export(db, location=n.location, vehicle_model=n.vehicle_model, bom_version=n.bom_version); print(name, len(data)); db.close()"
```
