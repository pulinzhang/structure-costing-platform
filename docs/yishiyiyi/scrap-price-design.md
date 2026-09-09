# 废料月度销售价

> **状态：应用已落地**（库表此前已迁）。  
> 表：`stamping_scrap_prices`。切片：`yishiyiyi`。  
> 基地：[location-design.md](../masterdata/location-design.md)。引用保护：架构宪法 §4.3。  
> 现网页：`#/scrap-price`。权限码不变。

---

## 0. 一句话

**一行 = 年 + 月 + 采购基地规范名 + 废料类别。** 类别只有两种。页面按类别录入；有多少已启用基地，矩阵就多少行。有废料价的基地不能删。

核价取价只吃 **钢材**。铝板价只在本页维护，本期不进零件公式。

---

## 1. 库已定（不要再迁字面量）

列 `scrap_category` 已有。唯一键 `(location, scrap_category, year, month)`。假地点 `location='铝板'` 已删；铝板价已按五座基地落行。

| 库值 | 页面文案 |
|------|----------|
| `钢材` | **钢材料** |
| `铝板` | **铝材** |

禁止再发明第三类，禁止把「铝板」写回 `location`。不要把库值改成「钢材料 / 铝材」。

---

## 2. 和基地的关系

废料价是基地的 **直接下一跳**（子表声明 FK，父不知）。

```text
locations.location  ←  stamping_scrap_prices.location
                      ForeignKey ON DELETE RESTRICT + ON UPDATE RESTRICT
```

- 还有废料价行（任一类别、任一月）→ 删基地 / 改规范名：`IntegrityError` → `仍被引用，不能删除` / `仍被引用，不能修改`。
- 基地 Model **禁止** `relationship` 指向本表。
- 写入：每行 `location` 经 `LocationService.require_enabled`，只落规范名。禁用基地不能新录。
- 矩阵行：`list_enabled`，顺序 `sort_order`。**废止** `SCRAP_PRICE_LOCATIONS` 与「固定 6 行」。
- 新启用一座基地：下一次打开月份矩阵自动多一行空模板，不代建价。
- 禁用：已有价仍占 FK；该月再保存当前类别时，覆盖集只有已启用基地（禁用基地该类当月旧行会被覆盖删掉）。要留档就先别保存、或先把价删干净再禁用。

列表筛 / 引擎跳转的基地选项：`list_registered` + `expand_for_query`。禁止本表 `DISTINCT location`。

---

## 3. 页面

仍是单页叶子 `#/scrap-price`。在年份/月份时间轴旁加 **双按钮**（形态对齐采购价格页，不要下拉、不要第三项）：

```text
[ 钢材料 ]  [ 铝材 ]
     ↑ 左、默认           ↑ 右
scrap_category=钢材       scrap_category=铝板
```

点即改类别并重新拉该月矩阵。保存 / 复制 / 删除本月 **只动当前类别**。

矩阵列仍是：基地 · 大盘价 · 扣费 · 净价 · 备注。行 = 已启用基地。页脚写 `{n} 个基地`，禁止写死「6 个基地」。

齐全：当前类别下，每个已启用基地都有净价。`filled_count / n`，`n = list_enabled` 条数。

---

## 4. 写与复制

**保存（PUT `/month`）**

- Query 或 body 必带 `scrap_category`（只允许 `钢材` | `铝板`）。
- `items` 必须恰好等于 **当前已启用基地** 集合（规范名、不重复、可按 `sort_order` 重排）。少了、多了、或出现「铝板」当地点 → 400。
- 净价仍由服务端算：大盘 − 扣费。
- 覆盖范围：`year + month + scrap_category`。**禁止**再按「整月删光再插入」（会把另一类一并删掉）。

**复制月度**

- 复制 **当前类别** 的全部已启用基地行到目标年月同类。
- 源月该类对已启用基地必须齐全，否则 400，列出缺的基地。
- 源月另一类有没有、齐不齐，不管。
- 目标月该类已有数据：覆盖该类，不动另一类。
- 面板文案 `已有 x/n` 的分母是已启用基地数，不是 6。

**删除本月**

- 只删当前类别该年该月。另一类留下。
- 两类都没有了才算该月在月份芯片上「尚未维护」。

---

## 5. API / 分层

路径仍 `/api/yishiyiyi/scrap-price`。月矩阵 GET/PUT/复制/删除/月份列表都带或返回 `scrap_category`。

```text
Router → yishiyiyi ScrapPrice Service
           ├── LocationService（list_enabled / require_enabled / expand_for_query）
           └── ScrapPriceRepository
```

- Model 加 `scrap_category`；`location` 注释只写基地；FK 如上；唯一约束与现库一致。
- `get_by_location_year_month` 必带 `scrap_category`。
- 核价 `PriceResolver.find_scrap_price`、引擎门禁：固定 `钢材`。同基地有铝板行时禁止 `.first()` 不带类别。
- 仪表盘「废料是否齐全」：按核算基地查 **钢材** 该月有没有净价；禁止再用「6 行填满」。
- 导出：按类别分块或分 Sheet；列随已登记/已启用基地变。禁止再输出名为「铝板」的地点列。
- 废止 `app/common/scrap_price_locations.py`。类别常量放 `app/common/scrap_categories.py`（`钢材` / `铝板`）。
- 种子按新键写，不再写 `location=铝板`。

月份芯片 `is_complete`：该月 **当前查看类别** 是否对已启用基地齐全；列表若一次返回两类，用两个计数，不要把两类行数加在一起当「/6」。

---

## 6. 明确不做（本期）

- 按材质把铝件核价改吃铝板价
- 第三种类别、按基地再拆铝价
- 基地页去 count 废料行（拦删除只靠 FK）
- 给钢价 / 零件表加基地外键（仍不是下一跳）

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 应用落地：分类录入；行=已启用基地；FK 拦删基地；核价只取钢材。 |
| 2026-09-09 | 应用设计：类别录入；行=已启用基地；FK 拦删基地；核价仍只取钢材。库表已迁、应用未做。 |
