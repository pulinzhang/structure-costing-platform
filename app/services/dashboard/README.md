# 仪表盘 Service（`dashboard/`）

下游组合上游切片，输出管理者待办 / 就绪 / 本期产出。不算账。

| 你要做什么 | 调 |
|---|---|
| 看板汇总 | `dashboard_service.DashboardService` |

禁止本包 `__init__.py` 再导出。HTTP 仍在 `/api/dashboard`。

对外入口：`DashboardService`（`dashboard_service.py`）。

## 架构

门面注入各切片 Repository，委托 `attention` / `readiness` / `scope` / `scrap` / `coverage`。

## 职责

| 模块 | 职责 |
|------|------|
| `dashboard_service.py` | 看板汇总编排、钢价计算页统计入口 |
| `attention.py` | 关注项文案、严重度、跳转页 |
| `readiness.py` | 就绪度勾选、本期待审产出 |
| `scope.py` | 默认年/月/基地/项目 |
| `scrap.py` | 废料月度价齐套 |
| `coverage.py` | BOM 覆盖、基价/政策条数、钢价筛选项 |
