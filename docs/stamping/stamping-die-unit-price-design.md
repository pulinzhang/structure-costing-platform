# 冲压模具单价档案

> **状态：已落地（仅档案维护）。**  
> 关联：[冲压件模具管理](stamping-die-management-design.md)（布点几何，不算额）。  
> 硬约束：分层与切片见 [architecture.md](../architecture.md)。

---

## 0. 一句话

按 **采购基地 + 项目** 维护钢板模 / 级进模单价、项目分摊数量、生效状态。这是核价**档案**（不是结果台账）：本表不写年度模具费金额。

下游只读：年度模具费计算、核价引擎硬门 `die_unit_price`（有布点年交集的项目须有生效档且分摊万台有效）。见 [stamping-die-fee-design.md](stamping-die-fee-design.md)、[costing-engine-design.md](../costing/costing-engine-design.md) §5.1 / §5.2。

---

## 1. 范围

| 做 | 不做 |
|---|---|
| 手工 CRUD | Excel 上传、file_trace |
| 唯一键 `location` + `vehicle_model` | 版本、冲压厂 |
| 状态 `effective` / `invalid` | 审核流、产量累计、自动满寿 |
| 筛选项来自冲压工艺库 | 改布点主表、回写 `alloc_status` |

新增须该基地+项目即可（不依赖 `stamping_parts`）。细则见 [stamping-apqp-die-before-process-design.md](stamping-apqp-die-before-process-design.md)。**唯一键**（基地+项目）在 Service 新增/修改保存时校验，返回可读中文提示；库唯一约束只作兜底，不把数据库错误给用户。修改保存也会带上基地+项目并排除本条后查重。

---

## 2. 字段

| 字段 | 说明 |
|------|------|
| `location` | 采购基地 |
| `vehicle_model` | 项目（`normalize_vehicle_model`） |
| `steel_plate_unit_price` | 钢板模，万元/吨，`Decimal` |
| `progressive_die_unit_price` | 级进模，万元/吨 |
| `allocation_qty` | 项目分摊数量（万台），正整数 `Decimal`，默认 10，JSON 不带小数位 |
| `status` | `effective` 生效 / `invalid` 失效 |

铸造模取价留给计算层（可并入钢板模档），本表不单列。

---

## 3. 接口

前缀 `/api/stamping/die-unit-prices`。

- `GET /filters` — 基地 / 项目（工艺级联）
- `GET /` — 分页；`location` / `vehicle_model` / `status` 可选
- `POST /` — 新增 201
- `PUT /{id}` — 可改基地、项目、单价、分摊数量、状态；改作用域时仍校验工艺存在且不与其它档案冲突
- `DELETE /{id}` — 单条删除

唯一键只在 Service 校验（前端不预查）。冲突 HTTP 409，中文提示引导去改已有记录。

页面：`#/stamping-die-unit-price`。权限：`menu:stamping-die-unit-price` + `view` / `create` / `update` / `delete`。

---

## 4. 修订

| 日期 | 说明 |
|---|---|
| 2026-09-19 | 纠正「不进 costing」：档案只读；引擎硬门 `die_unit_price` + 年度模具费计算消费本表 |
| 2026-08-30 | 初稿：基地+项目唯一键，钢板模/级进模单价与分摊万台 |
