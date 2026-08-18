# 中标钢厂厚度价格一览 Service（`yishiyiyi/winning_thickness`）

> 一事一议 · 中标钢厂厚度价格一览（派生报表）  
> 路径：`app/services/yishiyiyi/winning_thickness/`

采用「根门面 + 按关注点子包」组织，与 `yishiyiyi/policy`、`yishiyiyi/base_price` 一致。

---

## 1. 业务范围

按基地 + 年 + 月，取该期基准价，匹配厚度加减价政策（钢厂别名与钢材联动算价一致），展开厚度区间：

**最终价 = 基准价 + 厚度加减价 + 加工费**

| 能力 | 说明 |
|------|------|
| 行组装 | 去重基价、匹配 THICKNESS 政策、展开阶梯行 |
| 预览分页 | 内存分页返回 VO |
| Excel 导出 | 与前端预览列一致（含弱化溯源列） |

**对外入口**：

```python
from app.services.yishiyiyi.winning_thickness import WinningThicknessExportService
```

本切片无独立 CRUD / 导入：数据来自 `base_price` 与 `policy` 主数据。

---

## 2. 为什么这样组织

1. **组装与 Excel 分离**  
   政策匹配、区间展开与 openpyxl 样式无关：改匹配看 `assemble/`，改表样看 `export/excel_exporter.py`。

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
├── winning_thickness_export_service.py   # 薄门面
├── assemble/
│   └── row_assembler.py                  # 基价×厚度阶梯行组装
└── export/
    └── excel_exporter.py                  # openpyxl
```

---

## 4. 依赖方向

```text
Router
  └── WinningThicknessExportService
        ├── assemble.WinningThicknessRowAssembler
        │     ├── base_price Repository
        │     ├── policy Repository
        │     └── costing.steel_price 匹配公共函数
        └── export.WinningThicknessExporter
```

| 子包 | 负责 | 不负责 |
|------|------|--------|
| `assemble/` | 去重、政策命中、展开 VO | xlsx |
| `export/` | 表头/弱化列/溯源文本/工作簿 | 政策匹配 |

---

## 5. 关键业务约定

- 必填：年、月、基地。  
- 厚度政策：`policy_type == THICKNESS` 且 `grade_value` 等于牌号；优先 `base_thickness` 一致。  
- 无政策或无厚度阶梯：仍输出一行，加减价为 0，厚度范围为 `-`。  
- 区间文案复用 `policy.export.excel_exporter.format_interval`。

---

## 6. 扩展时改哪里

| 需求 | 落点 |
|------|------|
| 匹配规则 / 展开逻辑 | `assemble/row_assembler.py` |
| 导出列或样式 | `export/excel_exporter.py` |
| 预览分页策略 | 门面 `preview` |

---

## 7. 相关路径

| 层级 | 路径 |
|------|------|
| Router | `app/routers/yishiyiyi/winning_thickness/` |
| 依赖 Service | `yishiyiyi/base_price`、`yishiyiyi/policy` |
| 匹配公共 | `costing/steel_price/calc/steps/adjustments/common` |
| 前端 | `static/js/features/yishiyiyi/winning-thickness/` |
| API 前缀 | `/api/yishiyiyi/winning-thickness` |
| 对照结构 | `app/services/yishiyiyi/base_price/` |
