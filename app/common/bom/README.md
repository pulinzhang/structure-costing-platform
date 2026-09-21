# BOM 公共能力（`app/common/bom/`）

> 无业务编排归属、被 BOM / 核价多方复用的纯契约与工具。  
> **禁止**在此写 Router / Service 事务 / 落库；改目录发版即可，暂不做独立 CRUD 功能。

---

## 1. 焊接标准工艺目录

**唯一真相**：[`welding_standard_process.py`](./welding_standard_process.py)

| 内容 | 符号 |
|------|------|
| 标准工艺名称 | `WeldingStandardProcessName`（`StrEnum`） |
| 目录单位 | `STANDARD_PROCESS_UNIT` |
| 拆解原文 token → 标准名 | `TOKEN_TO_STANDARD_PROCESS` / `resolve_standard_process_name` |
| 列出目录 | `list_welding_standard_catalog()` → `(名称, 单位)` |
| 单价门禁 | `validate_welding_unit_price_catalog(name, unit)` |

业务约定：名称与单位须与目录**完全一致**（导入、手工创建、拆解明细映射、L0 焊接费按名匹配单价）。  
当前用代码枚举写死；**以后若要在线增删改，再落库做成独立主数据功能**——在此之前以本模块为准。

### 1.1 以后加一项标准工艺（改 Python）

按顺序改同一文件，发版即可：

1. 在 `WeldingStandardProcessName` 增加枚举项（中文 `value` 即业务名，如 `"焊点"`）
2. 在 `STANDARD_PROCESS_UNIT` 补「名称 → 单位」
3. 若拆解原文能自动映射：在 `TOKEN_TO_STANDARD_PROCESS` 增加 token（不能唯一确定则映射为 `None`）
4. （可选）焊接单价导入模板示例价：`app/services/bom/welding_unit_price/importing/service.py` 的 `_TEMPLATE_SAMPLE_PRICES`
5. 若前端拆解页仍硬编码 `STANDARD_PROCESS_UNIT`，同步或改为拉目录 API，避免双份真相

门禁与模板会随 `list_welding_standard_catalog()` / `validate_welding_unit_price_catalog` 自动带上新项。

### 1.2 谁在用

| 消费方 | 用途 |
|--------|------|
| 焊接单价 DTO / Parser / Service | 名称·单位门禁 |
| 焊接单价导入模板 | 「焊接单价」示例行 + 「标准工艺目录」工作表 |
| `GET /api/bom/welding-unit-price/standard-catalog` | 只读目录（入口挂在单价路由，**概念上属本公共契约**） |
| 焊接工艺拆解 Parser / Service | token 映射、编辑校验 |
| L0 焊接费计算 | 按标准工艺名匹配单价 |
| 拆解 L0 核对导出 | 标准工艺 / 标准单位列（见 `welding_process_breakdown/export/README.md`） |

### 1.3 刻意不做的事（现阶段）

- 不做独立侧栏页、不做目录表 CRUD
- 不把目录搬进「焊接单价」切片私有代码（避免拆解 / L0 反向依赖单价）

---

## 2. 同包其它模块

| 文件 | 职责 |
|------|------|
| `manufacturing_category.py` | 制造类别集合、短零件号规则 |
| `welding_billing_qty.py` | 计费用量 / 单位规范化（单价门禁单位比较会用到） |

---

## 3. 相关测试

- `tests/bom/test_welding_unit_price_catalog_gate.py` — 目录门禁与 `list_standard_catalog`
