# 中标钢厂厚度价格列表 Service（`yishiyiyi/winning_thickness`）

> 一事一议 · 中标钢厂厚度价格列表（派生报表）  
> 路径：`app/services/yishiyiyi/winning_thickness/`

采用「根门面 + 按关注点子包」组织，与 `yishiyiyi/policy`、`yishiyiyi/base_price` 一致。

---

## 1. 业务范围

按可选的基地 / 年 / 月（空=不限）取中标基价，匹配厚度加减价政策（钢厂别名与钢材联动算价一致），展开厚度区间：

**最终价 = 基准价 + 厚度加减价 + 加工费**

| 能力 | 说明 |
|------|------|
| 行组装 | 基价表驱动；档案大类 × CATEGORY 厚度政策；逐牌号展开全部厚度区间；无筛时跨账期按基价行自身年月匹配政策 |
| 预览分页 | 内存分页返回 VO；打开即全量 |
| Excel 导出 | 三页：阅读用一览（含弱化溯源）、计算用、使用示例；**仅含有基价的行**；须选定年度和月份 |

**对外入口**：

```python
from app.services.yishiyiyi.winning_thickness.export.service import (
    WinningThicknessExportService,
)
```

本切片无独立 CRUD / 导入：数据来自 `base_price` 与 `policy` 主数据。

---

## 2. 为什么这样组织

1. **组装与 Excel 分离**  
   政策匹配、区间展开与 openpyxl 样式无关：改匹配看 `assemble/`，改表样看 `export/`。

2. **门面只做委托**  
   `WinningThicknessExportService` 提供 `build_rows` / `preview` / `export`，细节在子包。

3. **复用上游政策匹配**  
   钢厂/大类别名、base_thickness 优先顺序与钢材联动加减价一致，统一走
   `yishiyiyi.policy.match.adjustment_common`（`filter_candidates` /
   `order_by_base_thickness`），不反向依赖 costing。

4. **仍遵守项目分层**  
   只读 Repository；不写主数据；Router 经门面取数。

---

## 3. 目录结构

```text
app/services/yishiyiyi/winning_thickness/
├── README.md
├── __init__.py
├── assemble/
│   └── row_assembler.py                  # 基价×厚度阶梯行组装
└── export/
    ├── service.py                        # 薄门面
    ├── excel_exporter.py                 # 组工作簿
    ├── letterhead.py                     # 外发抬头
    ├── overview_sheet.py                 # 阅读页
    ├── calc_sheet.py                     # 计算页
    ├── example_sheet.py                  # 使用示例页
    ├── values.py                         # 列布局 / 溯源 / 摘录
    └── styles.py                         # 色板字体
```

---

## 4. 依赖方向

```text
Router
  └── WinningThicknessExportService
        ├── assemble.WinningThicknessRowAssembler
        │     ├── base_price Repository（驱动行）
        │     ├── steel_grade_category Repository（大类 → 政策）
        │     ├── policy Repository
        │     └── policy.match.adjustment_common
        └── export.WinningThicknessExporter
```

| 子包 | 负责 | 不负责 |
|------|------|--------|
| `assemble/` | 基价去重、档案取大类、按 CATEGORY 政策逐牌号展开 VO | xlsx |
| `export/` | 工作簿 / 抬头 / 三页表样；入口过滤无基价溯源行 | 政策匹配、查库补行 |

---

## 5. 关键业务约定

- 必填：年、月、基地。  
- **以基价表为据**：当期该基地无基价行的牌号不输出（无基价则厚度加减价无业务意义）。  
- 大类：牌号分类档案 `category_name`（冷轧/镀锌/酸洗），用于命中 CATEGORY 厚度政策。  
- 厚度政策：`policy_type == THICKNESS` 且 `grade_type == CATEGORY`；同大类各牌号共用阶梯并各输出全部厚度区间；优先 `base_thickness` 一致。  
- 无政策或无厚度阶梯：不输出（预览/导出仅展示有效阶梯行）。  
- 区间文案复用 `policy.export.excel_exporter.format_interval`。  
- 计算页最终价为 Excel 公式 `基准价+加减价+加工费`；使用示例页从本批真实行摘录，下部附公式说明。

---

## 6. 职责

| 模块 | 职责 |
|------|------|
| `assemble/row_assembler.py` | 匹配规则 / 展开逻辑 |
| `export/letterhead.py` | 外发抬头 / 打印 |
| `export/overview_sheet.py` | 阅读页列或样式 |
| `export/calc_sheet.py` | 计算页列或公式 |
| `export/example_sheet.py` | 示例页摘录 / 公式说明 |
| `export/styles.py` | 色板字体 |
| 门面 `preview` | 预览分页 |

---

## 7. 相关路径

| 层级 | 路径 |
|------|------|
| Router | `app/routers/yishiyiyi/winning_thickness.py` |
| 依赖 Service | `masterdata/steel_grade_category`、`yishiyiyi/base_price`、`yishiyiyi/policy` |
| 匹配公共 | `yishiyiyi/policy/match/adjustment_common` |
| 前端 | `static/js/features/yishiyiyi/winning-thickness/` |
| API 前缀 | `/api/yishiyiyi/winning-thickness` |
| 对照结构 | `app/services/yishiyiyi/base_price/` |
