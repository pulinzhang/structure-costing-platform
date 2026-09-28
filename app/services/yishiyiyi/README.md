# 一事一议 Service（`yishiyiyi/`）

钢价政策切片根。包名沿用 `yishiyiyi`，不要再引入第二套英文包名。

| 你要做什么 | 打开 |
|---|---|
| 厚度加减价政策 | `policy/` |
| 钢材基准价格 | `base_price/` |
| 废料月度销售价 | `scrap_price/` |
| 中标钢厂厚度价格列表 | `winning_thickness/` |

禁止本包 `__init__.py` 再导出。

HTTP：`/api/yishiyiyi/policy`、`/api/yishiyiyi/base-price`、`/api/yishiyiyi/scrap-price`、`/api/yishiyiyi/winning-thickness`。

## 目录

| 目录 | 职责 |
|------|------|
| `policy/` | 政策主表与阶梯匹配 |
| `base_price/` | 基准价格 CRUD / 导入 |
| `scrap_price/` | 废料月度价矩阵 |
| `winning_thickness/` | 派生一览报表 |
