# 钢价政策 Sheet 处理器基类（`base_handler`）

> 一事一议 · 加减价政策 Excel 解析 · Handler 公共内核  
> 路径：`app/parsers/yishiyiyi/policy/handlers/base_handler/`

各钢厂 Handler（马钢 / 唐钢 / 首钢 / …）继承 `BaseSheetHandler`，在此包内复用单元格扫描、块定位、政策装配与锌层/厚度通用解析。

---

## 1. 设计原则

**基类只做编排，不做专用表解析。**

| 组件 | 职责 | 禁止 |
|------|------|------|
| `BaseSheetHandler` | `parse()` 编排、子类钩子、兼容委托 | 堆锌层/厚度等专用表逻辑 |
| `SheetScanner` | openpyxl 读写、行列探测、合并格 | 业务语义（加减价规则） |
| `PolicyAssembler` | 块定位、边界推断、阶梯项/政策构建 | 直接写库 |
| `ThicknessBlockFinder` | 默认「厚度加减价」块扫描 | 宽度块 / 锌层 |
| `ZincCoatingParser` | 「锌层加价」表查找与解析 | 厚度/宽度通用块 |

历史上曾把锌层、厚度扫描、装配委托全塞进 `BaseSheetHandler`（上帝类）。现已按关注点拆出，基类仅保留薄委托以便子类 API 稳定。

---

## 2. 目录结构

```text
base_handler/
├── README.md
├── __init__.py                 # 对外导出
├── base_handler.py             # BaseSheetHandler：编排 + 钩子 + 薄委托
├── sheet_scanner.py            # SheetScanner：单元格原语
├── policy_assembler.py         # PolicyAssembler：业务语义装配
├── thickness_block_finder.py   # ThicknessBlockFinder：默认厚度块
└── zinc_coating.py             # ZincCoatingParser：锌层加价
```

**导入：**

```python
from app.parsers.yishiyiyi.policy.handlers.base_handler import (
    BaseSheetHandler,
    PolicyAssembler,
    SheetScanner,
    ThicknessBlockFinder,
    ZincCoatingParser,
)
```

---

## 3. 解析流水线

```text
registry.find_handler(sheet_name)
        │
        ▼
ConcreteHandler.parse(sheet, steel_mill, warnings)
        │
        ├─► find_thickness_blocks() / find_width_blocks()   # 子类覆写
        │         │
        │         └─► 常复用 find_default_thickness_blocks()
        │                   └─► ThicknessBlockFinder
        │
        ├─► assembler.build_policies_from_block(...)       # 块 → ParsedPolicy
        │
        └─► parse_zinc_coating_blocks(...)                 # 可选
                  └─► ZincCoatingParser
```

默认 `BaseSheetHandler.parse()`：

1. `_parse_blocks(..., "THICKNESS")`
2. `_parse_blocks(..., "WIDTH")`
3. `parse_zinc_coating_blocks(...)`

子类可整体覆写 `parse()`（如马钢旧版固定区域），或只覆写 `find_*_blocks` / `_parse_blocks`。

---

## 4. 块描述约定

厚度 / 宽度块统一用 dict 描述（再交给 `PolicyAssembler`）：

```python
{
    "category_name": str,       # 如 冷轧钢 / 镀锌钢
    "policy_type": str,         # "THICKNESS" | "WIDTH"
    "grade_col": int,           # 钢种列
    "header_row": int,          # 边界列头行
    "price_cols": list[int],    # 价格列
    "data_row_start": int,
    "data_row_end": int,
    "base_thickness": Decimal | None,
}
```

锌层块由 `ZincCoatingParser` 使用另一套字段（`label_row` / `zinc_cols` / `zinc_ranges` 等），最终仍产出 `ParsedPolicy`。

---

## 5. 子类怎么用

### 5.1 最小覆写（多数钢厂）

```python
class XxxSheetHandler(BaseSheetHandler):
    def find_thickness_blocks(self, sheet, steel_mill):
        return self.find_default_thickness_blocks(sheet, steel_mill)

    def find_width_blocks(self, sheet, steel_mill):
        # 钢厂专用宽度定位，或 return []
        ...
```

### 5.2 直接用组件（推荐新代码）

```python
# 读单元格
self.scanner.text(sheet, row, col)
self.scanner.row_max(sheet)

# 语义装配
self.assembler.locate_width_block(...)
self.assembler.build_policies_from_block(sheet, steel_mill, block)
```

### 5.3 兼容委托（旧子类仍可用）

基类仍转发下列方法，避免大面积改各钢厂 Handler：

| 委托到 Scanner | 委托到 Assembler |
|----------------|------------------|
| `text` / `text_or_none` | `locate_thickness_block` / `locate_width_block` |
| `row_max` / `col_max` | `_collect_boundaries` / `_build_items_for_row` |
| `find_start_row` / `find_block_end_row` | `_infer_grade_type` / `infer_block_category` |
| `collect_price_cols` / `find_grade_label_rows` | `category_from_grade_name` |

新逻辑优先写 `self.scanner` / `self.assembler`，不要再往基类加业务方法。

---

## 6. 线程与实例

每个 `BaseSheetHandler` 实例在 `__init__` 中创建自己的：

- `SheetScanner`
- `PolicyAssembler`（共用上述 scanner）
- `ZincCoatingParser`
- `ThicknessBlockFinder`

`registry.find_handler()` 每次返回新实例，后台导入线程之间不共享 Handler 状态。

---

## 7. 改代码时看哪里

| 要改什么 | 打开 |
|----------|------|
| 默认厚度块怎么扫 | `thickness_block_finder.py` |
| 锌层加价表 | `zinc_coating.py` |
| 边界/阶梯项/政策怎么拼 | `policy_assembler.py` |
| 合并格、找标题行、扫价格列 | `sheet_scanner.py` |
| parse 顺序 / 子类钩子 | `base_handler.py` |
| 按 sheet 名选 Handler | 上级 `handlers/registry.py` |

**不要**再把钢厂专用或表专用逻辑塞回 `BaseSheetHandler`。
