# 钢材价格 Service（`steel_price/`）

查询 / 手工维护 / 审核 / 计算落库。联动计算编排在 `calc/`。

对外入口：`SteelPriceService`（`service.py`）。

## 架构

门面持有 `SteelPriceRepository`，方法委托同目录模块函数。

## 职责

| 模块 | 职责 |
|------|------|
| `service.py` | 对外入口、公式版本常量 |
| `paginate.py` | 列表分页、筛选下拉、HUD 汇总 |
| `crud.py` | 单条增删改、按条件批量删除 |
| `audit/service.py` | 按年+月+基地批量审核、反审核 |
| `calc_batch.py` | 计算批次落库（已审不覆盖） |
| `pricing.py` | 最终价公式、规格补全、已审保护 |
| `calc/` | 联动计算编排 |
| `export/` | 钢价结果 Excel |
