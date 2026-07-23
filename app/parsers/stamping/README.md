# 冲压工艺 Excel 解析器

> **Parser 的职责只有一个：将冲压工艺 Excel 稳定、可预测地转换为统一的 ParserResult。**

解析奇瑞 T28 等车型的冲压工艺确认表 Excel 文件，提取零件信息、工序信息、简图等数据。

## 快速开始

```python
from app.parsers.stamping import parse_stamping_excel, StampingExcelParser

# 方式一：便捷函数
result = parse_stamping_excel("冲压工艺确认表.xlsx")

# 方式二：类实例
parser = StampingExcelParser()
result = parser.parse("冲压工艺确认表.xlsx")

print(f"零件数: {result.part_count}, 工序数: {result.process_count}, 简图: {result.image_count}")
```

---

## 一、问题背景

### 1.1 冲压工艺 Excel 是什么样的？

冲压工艺确认表是汽车厂发给供应商的工艺文件，里面包含：

- **零件信息**：零件号、名称、材质、料厚、尺寸...
- **工序信息**：每一道冲压工序（拉伸、落料、冲孔...）
- **简图**：每个零件的示意图

### 1.2 解析这个 Excel 有什么难点？

```
┌─────────────┬────────────┐
│ 零件号      │ 工序号      │
├─────────────┼────────────┤
│ 501006875AA │ OP10 拉伸   │ ← 零件行 + 第一道工序
├─────────────┼────────────┤
│             │ OP20 冲孔   │ ← 工序行（没有零件号）
├─────────────┼────────────┤
│             │ OP30 翻边   │ ← 工序行（没有零件号）
├─────────────┼────────────┤
│ 501006876AA │ OP10 拉伸   │ ← 零件行 + 第一道工序
├─────────────┼────────────┤
│             │ OP20 落料   │ ← 工序行
└─────────────┴────────────┘
```

问题：**第二行、第三行没有零件号，但它们属于第一个零件。**

---

## 二、解析流程

### 2.1 整体流程

```
Excel 文件
    │
    ▼
┌──────────────────────────────────────┐
│  StampingExcelParser                │
│  （流程编排器）                      │
│                                      │
│  负责：调用各个模块、协调工作流程      │
└──────────────────────────────────────┘
    │
    ├── 1. 加载 Excel
    │
    ├── 2. 识别 Sheet
    │
    ├── 3. 解析表头（确定列的位置）
    │
    ├── 4. 建立零件号范围缓存
    │
    ├── 5. 缓存解析
    │
    └── 6. 返回结果
    │
    ▼
ParserResult（零件列表、工序列表、简图、警告）
```

### 2.2 代码示例

```python
class StampingExcelParser:
    def parse(self, file_path: str) -> ParserResult:
        # 1. 加载 Excel
        excel_ctx = ExcelContext()
        excel_ctx.load(file_path)

        # 2. 识别 Sheet
        sheet = excel_ctx.find_sheet()

        # 3. 解析表头
        header_resolver = HeaderResolver()
        header_ctx = header_resolver.resolve(sheet)
        # header_ctx 是一个 HeaderContext 对象，包含：
        #   - header_ctx.header_row      → 表头行号
        #   - header_ctx.data_start_row   → 数据起始行号
        #   - header_ctx.col_map          → 列映射 {字段名: 列号}

        # 4. 建立零件号范围缓存
        # 为什么要缓存？因为 Excel 里零件号列用了合并单元格
        # 一个零件号会跨越多行，比如：
        #   第5行：501006875AA （合并了 5-7 行）
        #   第6行：空（但值还是 501006875AA）
        #   第7行：空（但值还是 501006875AA）
        #
        # build_merged_cache() 会扫描所有合并单元格，建立一个范围列表：
        # [
        #     PartNoRange(value="501006875AA", start_row=5, end_row=7),
        #     PartNoRange(value="501006876AA", start_row=8, end_row=10),
        # ]
        excel_ctx.build_merged_cache(header_ctx.col_map["part_no"])

        # 5. 缓存解析
        # 解析每一行数据
        for row in range(header_ctx.data_start_row, sheet.max_row + 1):
            # 根据行号查缓存，快速知道这一行属于哪个零件
            # 例如：row=6 → PartNoRange(value="501006875AA", start_row=5, end_row=7)
            range_info = excel_ctx.get_part_no_range(row)
            # 如果 range_info 不是 None，说明这一行属于某个零件
            # 如果是 None，说明这行没有零件号（只有工序信息）
            # ...

        # 6. 返回结果
        return ParserResult(...)
```

---

## 三、为什么要拆分？

先问一个问题。

### 3.1 如果不拆分，会怎样？

如果把所有代码都写进 `parse()`，程序大概长这样：

```python
def parse(file_path: str) -> ParserResult:
    # 打开 Excel
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active

    # 找 Sheet
    for s in wb.sheetnames:
        if "工艺" in s:
            sheet = wb[s]
            break

    # 找 Header
    for row in range(1, 20):
        cell = sheet.cell(row, 1).value
        if cell and "零件号" in str(cell):
            header_row = row
            break

    # 构建列映射
    col_map = {}
    for col in range(1, 30):
        val = sheet.cell(header_row, col).value
        if val:
            if "零件号" in str(val):
                col_map["part_no"] = col
            elif "工序" in str(val):
                col_map["process"] = col
            # ... 更多列

    # 处理合并单元格
    merged_ranges = {}
    for merged_range in sheet.merged_cells.ranges:
        if merged_range.min_col == col_map["part_no"]:
            start_row = merged_range.min_row
            end_row = merged_range.max_row
            value = sheet.cell(start_row, col_map["part_no"]).value
            for r in range(start_row, end_row + 1):
                merged_ranges[r] = value

    # 逐行解析
    parts = []
    processes = []
    for row in range(header_row + 1, sheet.max_row + 1):
        part_no_cell = sheet.cell(row, col_map["part_no"]).value
        part_no = part_no_cell or merged_ranges.get(row)

        if part_no:
            # 解析零件行
            part_name = sheet.cell(row, col_map["name"]).value
            material = sheet.cell(row, col_map["material"]).value
            # ... 更多字段
            parts.append({...})
        else:
            # 解析工序行
            process_seq = sheet.cell(row, col_map["seq"]).value
            process_code = sheet.cell(row, col_map["code"]).value
            # ...
            processes.append({...})

    # 转换数值
    for part in parts:
        thickness = part.get("thickness")
        if thickness and "/" in str(thickness):
            # 分数转小数
            nums = thickness.split("/")
            part["thickness"] = float(nums[0]) / float(nums[1])

    # 保存图片
    images = {}
    for img in sheet._images:
        # ...

    # 返回结果
    return ParserResult(parts=parts, processes=processes, ...)
```

程序当然可以运行。

但是半年以后……

客户换了一种新的 Excel，表头位置变了。

现在需要修改：

```
# 找 Header
for row in range(1, 20):
    ...
```

可是：

你敢保证不会影响

```
# 处理合并单元格
...

# 逐行解析
...

# 转换数值
...
```

吗？

**没人敢保证。**

### 3.2 怎么拆？

所以，我们开始思考。

这些事情，是不是在解决不同的问题？

```
问题1：怎么读取 Excel？
问题2：怎么找到表头？
问题3：怎么解析每一行？
问题4：怎么转换数值？
```

答案是：**是。**

于是我们把它们拆开：

```
┌─────────────────┐    ┌─────────────────┐
│  ExcelContext   │    │  HeaderResolver │
│  怎么读写Excel？ │    │  怎么找表头？  │
└─────────────────┘    └─────────────────┘

┌─────────────────┐    ┌─────────────────┐
│    RowParser    │    │   ValueParser   │
│  怎么解析行？   │    │  怎么转数值？   │
└─────────────────┘    └─────────────────┘
```

每个模块围绕同一个问题组织代码。

### 3.3 重要原则

> **关注点分离，并不是把代码拆得越碎越好，而是让每一段代码都围绕同一个问题展开。**

举个例子：

```
❌ 不好的拆分

HeaderFinder
HeaderValidator
HeaderBuilder
HeaderMapper
HeaderCache

虽然每个类都只有几十行，

但开发者需要不停地在多个文件之间切换。
```

```
✅ 更好的拆分

HeaderResolver

    find_header()
    build_context()
    build_col_map()

三个方法，一个类。

因为这些方法共同在回答：Header 如何解析。
```

---

## 四、一个真实的重构过程

### 4.1 最初的样子

最开始，Parser 长这样：

```
stamping_parser.py

    │
    ├── 685 行
    ├── 一个类
    └── 什么都干
```

打开这个文件，你会看到：

- Excel 读写代码
- 表头识别代码
- 行列解析代码
- 数值转换代码
- 图片处理代码
- 错误处理代码

全搅在一起。

### 4.2 第一步：把 Excel 操作抽出来

发现：文件读写、单元格访问、合并单元格处理，这些代码到处都在用。

抽出来：

```
ExcelContext

    load()
    get_value()
    build_merged_cache()
    get_part_no_range()
```

Parser 减少 100 行。

### 4.3 第二步：把表头解析抽出来

发现：找表头、判断列、构建映射，这段逻辑很长，而且以后可能会变（不同车型、不同供应商）。

抽出来：

```
HeaderResolver

    resolve()
    find_header_row()
    build_col_map()
```

Parser 再减少 150 行。

### 4.4 第三步：把数值转换抽出来

发现：厚度字段有分数（如 `1/2`），重量字段有逗号（如 `1,234`），这些格式处理逻辑散落在各处。

抽出来：

```
ValueParser

    parse_decimal()
    parse_int()
    parse_tonnage()
```

Parser 又少了几十行。

### 4.5 最终结果

```
stamping_parser.py

    │
    ├── 280 行
    ├── 一个类
    └── 只负责组织流程
```

**好的架构不是设计出来的，而是一步一步重构出来的。**

---

## 五、数据模型（Data Model）

### 5.1 为什么需要数据模型？

这次重构的重点不是"让代码能运行"，而是"让代码能够表达业务"。

当一个函数返回 `Part` 时，调用者立刻知道它表示一个零件。

当一个函数返回 `Dict` 时，调用者必须打开源码才能知道里面有什么字段。

**好的类型，本身就是最好的文档（Good Types Are Self-Documenting）。**

### 5.2 类（Model）vs Dict

```
❌ 用 Dict 的问题

def parse_part_row(...) -> Dict[str, Any]:
    return {
        "part_number": "...",
        "part_name": "...",
        ...
    }

调用者必须：
1. 记住字段名称（拼写错误不会报错）
2. 知道每个字段的类型
3. 打开文档或源码才能理解
```

```
✅ 用类的好处

def parse_part_row(...) -> Part:
    return Part(part_number="...", part_name="...", ...)

调用者可以：
1. IDE 自动提示所有字段
2. 拼写错误会报错
3. 代码本身就是文档
```

### 5.3 数据模型一览

```
┌─────────────────┐
│   Excel 文件    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│  ExcelContext   │───▶│  PartNoRange    │
│  Excel 访问     │    │  零件号范围     │
└────────┬────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│  HeaderContext  │
│  表头信息       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│      Part       │    │    Process      │
│  零件           │    │  工序           │
└────────┬────────┘    └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
           ┌─────────────────┐
           │   ParserResult  │
           │  最终解析结果   │
           └─────────────────┘
```

### 5.4 模型详解

#### Part（零件）

表示冲压工艺表中的一个零件。

```python
from app.parsers.stamping import Part

part = Part(
    part_number="501006875AA",
    part_name="左前门外板",
    material="DC04",
    thickness=Decimal("0.8"),
    tonnage=800,
    ...
)

# 字段含义清晰
print(part.part_number)  # 零件号
print(part.thickness)     # 料厚（自动类型提示）
```

#### Process（工序）

表示冲压工艺表中的一个工序。

```python
from app.parsers.stamping import Process

process = Process(
    part_number="501006875AA",
    process_seq="OP10",
    process_code="拉伸",
    tonnage=800,
    ...
)
```

#### HeaderContext（表头上下文）

表示 Excel 表头解析的结果。

**为什么不用 Tuple？**

```python
# ❌ Tuple 的问题
header_row, data_start_row, col_map = header_resolver.resolve(sheet)
# 调用者必须记住顺序，必须看文档才知道每个值是什么

# ✅ HeaderContext 的好处
context = header_resolver.resolve(sheet)
context.header_row        # 语义清晰
context.data_start_row    # 语义清晰
context.col_map           # 语义清晰
context.header_paths      # 一目了然
```

#### PartNoRange（零件号范围）

表示零件号列的合并单元格范围。

```python
from app.parsers.stamping import PartNoRange

pr = PartNoRange(value="501006875AA", start_row=5, end_row=7)
print(pr.contains(6))  # True - 第6行属于这个零件
```

---

## 六、模块详解

### 6.1 ExcelContext（Excel 访问）

**解决的问题**：怎么读写 Excel？

```python
class ExcelContext:
    def load(self, file_path: str):
        """加载 Excel 文件"""

    def get_value(self, row: int, col: int):
        """获取单元格值（自动处理合并单元格）"""

    def get_part_no_range(self, row: int) -> Optional[PartNoRange]:
        """获取该行属于哪个零件号范围"""
```

### 6.2 HeaderResolver（表头解析）

**解决的问题**：怎么找到表头、确定每一列是什么？

```python
class HeaderResolver:
    def resolve(self, sheet) -> HeaderContext:
        """
        执行完整的表头解析流程。

        Returns:
            HeaderContext 对象，包含：
            - header_row: 表头行号
            - data_start_row: 数据起始行号
            - col_map: 列映射 {字段名: 列号}
            - header_paths: Header 路径
        """
```

### 6.3 RowParser（行解析）

**解决的问题**：怎么解析每一行数据？

```python
class RowParser:
    def parse_part_row(self, row_idx: int) -> Part:
        """解析零件行"""
        ...

    def parse_process_row(self, row_idx: int, part_number: str) -> Optional[Process]:
        """解析工序行"""
        ...
```

### 6.4 ValueParser（数值转换）

**解决的问题**：怎么把 Excel 里的字符串转换成数值？

```python
parse_decimal("1/2")    # → Decimal("0.5")
parse_decimal("1.25")   # → Decimal("1.25")
parse_int("100")        # → 100
```

---

## 七、核心设计：零件号范围缓存

### 7.1 问题

Excel 中零件号列使用了**合并单元格**：

```
    A列（零件号）
┌──────────────┐
│ 501006875AA  │ ← 这个值合并了 3 行
├──────────────┤
│              │ ← 空（但值还是 501006875AA）
├──────────────┤
│              │ ← 空（但值还是 501006875AA）
└──────────────┘
```

### 7.2 解决方案

**预先建立零件号范围表：**

```python
# 遍历 Excel 前，先扫描一遍合并单元格
ranges = [
    PartNoRange(value="501006875AA", start_row=5, end_row=7),
    PartNoRange(value="501006876AA", start_row=8, end_row=10),
    ...
]

# 解析时，直接查表
def get_part_no_range(row):
    for r in ranges:
        if r.start_row <= row <= r.end_row:
            return r
    return None
```

### 7.3 为什么不逐行判断？

```
❌ 逐行判断：
if row == 5: return "501006875AA"
if row == 6: return merged_cell(5)...
if row == 7: return merged_cell(5)...

问题：代码复杂，每次都要查合并单元格
```

```
✅ 预计算缓存：
ranges[row] → 零件号范围
```

---

## 八、非目标

**本 Parser 不负责：**

- 成本计算
- 数据库保存
- 业务校验
- Excel 导出
- UI 展示

**Parser 不保证业务数据正确性。**

Parser 的职责是尽可能准确地解析 Excel。

解析过程中发现的问题（如工序缺少代码），记录为 Warning，而不是抛异常。

---

## 九、设计原则

1. **Parser 只负责解析，不负责业务逻辑**
2. **每个模块围绕同一个问题组织代码**
3. **变化原因不同的功能，拆分成不同模块**
4. **遇到问题用 Warning 记录，而不是抛异常**
5. **模块之间传递领域对象（Model），而不是匿名 Dict**

---

**设计目标不是解析某一种 Excel，而是建立一种稳定、可预测、可扩展的 Excel → ParserResult 转换机制。**
