# 材料变更 — 1 表与解析器

> 落地：**第一刀代码。** 切点表 + 当月材料叠法（与第 4 刀同一套）+ 单测。  
> 不要做上传页。不改零件价计算器。  
> 契约：[00-contract.md](00-contract.md)　目录：[README.md](README.md)

切点表在本通道。当月材料只有 **`resolve_material`** 一份：门禁「变更前」调它（不含本本）；第 4 刀 `list_materials_as_of` 批量调它。`list_with_processes` 不叠。门禁常量放本通道包，禁止改 `app/common/`。

---

## 1. 工艺表不动

`stamping_parts` / `stamping_tailor_weld_blanks`：零 insert；零 update `material` / `version` / **生失效四列**；零同号第二行。上传、回滚都一样。

全部切点回滚完之后，该零件 `effective_year` / `effective_month` / `expiry_year` / `expiry_month` 必须仍是第一刀之前的字（115AA 工艺 2025年01月起那一套，不因 06/07 材料变更而改）。

不要复用 `engineering_change_upload_logs` / `orders` / `effect_links`。包路径现网已占：`app/models/engineering_change/material_change/`。

---

## 2. 上传头 `engineering_change_material_upload_logs`

| 列 | 要点 |
|----|------|
| `task_id` | `String(64)` 可空，索引 |
| `upload_file_id` | `Integer` FK `upload_files` RESTRICT。失败头若非空，文件行必须先在 |
| `status` | `String(20)`：`pending` / `success` / `failed` |
| `location` | `String(50)` |
| `vehicle_model` | `String(50)` |
| `stamping_supplier` | `String(100)` FK 供应商 RESTRICT。**必须有厂**，与表内「冲压工厂」同一规范全称 |
| `change_version` | `String(20)`，如 `MAT-202506` |
| `effective_year` / `effective_month` | `Integer`，月 1–12 |
| `original_filename` | `String(255)` |
| `message` | `Text` 可空 |
| 审计 | `AuditUserMixin`（`created_by` / `updated_by`） |

成功头 UNIQUE `(location, vehicle_model, stamping_supplier, change_version)` 只约束 `status=success`。同项目同月 **另一厂** 可以再有一本 `MAT-202506`。失败头、pending 不占成功版本。pending 另用 `ECM_PENDING_VERSION` 互斥（同基地+项目+厂+版本）。

---

## 3. 切点行 `engineering_change_material_orders`

Excel 一行 = 一刀。1 头 : N 行。

关键列（类型对齐设计变更单）：`upload_log_id` Integer FK 头 RESTRICT；`upload_file_id` Integer FK 文件 RESTRICT；`change_version` `String(20)`；`excel_row` Integer 可空（改图抄来的切点没有 Excel 行）；`location` `String(50)`；`stamping_supplier` `String(100)` FK 供应商 RESTRICT；`vehicle_model` `String(50)`；`effective_year` / `effective_month` Integer（**切点开始月，必须落库**）；`part_number` `String(50)`；`before_material` / `after_material` `String(50)`，FK **与 `stamping_parts.material` 同一条**（档案表现网名 `steel_grade_categories`，改字 CASCADE、RESTRICT 删档；**切点列禁止叫 `grade`**）；`before_thickness` / `after_thickness` `Numeric(10, 4)`（与工艺 `thickness` 同精度；**不叠回工艺料厚**）；`interchangeability` `String(20)` 存「不影响互换性」六字；`part_name` `String(200)`；`source_part_id` Integer FK 工艺 RESTRICT；`copied_from_order_id` Integer 可空 FK 本表切点 RESTRICT（**改图抄历史**：指向旧号那一行；Excel 上传的为空）；审计 Mixin。

索引：身份+生效月 UNIQUE；`source_part_id`；`upload_log_id`。

**不要**在切点行加 `expiry_year` / `expiry_month`，禁止为了「有效止」去 UPDATE 上一刀。有效时间按排队推（变更记录接口算出，不另存一列）：

| 切点 | 有效开始 | 有效结束 |
|------|----------|----------|
| 本刀生效月 | `effective_year` + `effective_month` | 下一刀生效月的前一月；没有下一刀 = **未结束** |

115AA 两刀配套：

| 版本 | 有效时间 | 变更前材料 | 变更前料厚 | 变更后材料 | 变更后料厚 |
|------|----------|--------|--------|--------|--------|
| `MAT-202506` | 2025年06月 ～ 2025年06月 | DC01 | 1.5 | DC03 | 1.5 |
| `MAT-202507` | 2025年07月 ～ 未结束 | DC03 | 1.5 | DC01 | 1.5 |

只有 06 月一刀时：`MAT-202506` 有效 2025年06月 ～ 未结束。

不要 `blank_seq` / `blank_part_number` / `source_blank_id`：拼焊整件拒，不按子片切。

硬 UNIQUE：

1. 切点 `(location, stamping_supplier, vehicle_model, part_number, effective_year, effective_month)`
2. 版本在成功头上 `(location, vehicle_model, stamping_supplier, change_version)`

下一刀生效月必须 **严格晚于** 该身份已有最晚切点。**变了还可以再变** = 再 insert 一行切点，禁止 UPDATE 上一刀、禁止改工艺 `material`、禁止插更早月或同月去改历史。

`403014115AA`：工艺永远 `DC01` / `V3-01`。第一刀 `MAT-202506` 变更前必须 = 当时最新 = `DC01`，变更后 `DC03`。第二刀配套 `MAT-202507` **再变回去**：变更前必须 = 当时最新 = `DC03`，变更后 `DC01`。

| as_of | 当月材料（库里最新） |
|-------|----------------------|
| 2025年05月 | `DC01` |
| 2025年06月 | `DC03` |
| 2025年07月起（第二刀后） | `DC01` |

---

## 4. 效果链接 `engineering_change_material_effect_links`

只为准回滚记账。`effect_kind` 只准 `material_cutover`。`after_id` 空。`before_id` = `source_part_id`。`order_id` FK 切点 RESTRICT。

回滚删序：链接 → 切点（含改图抄到新号的那些行，见第 5 刀）→ 头。不留 `rolled_back` 行。不改工艺行。拦法见第 3 刀：按 **基地 + 冲压工厂 + 项目 + 零件号** 还有没有更晚切点，不是「项目上随便一本更晚就全拦」。

---

## 5. 孤儿（FK）

解析按身份键 `(location, stamping_supplier, vehicle_model, part_number)`。SOP 再导是 **更新同行，行 id 不变**；记录接口可以按 `part_id` 找身份再查切点。

切点 `before_material` / `after_material` 与工艺 `material` 同一 FK：档案改字 CASCADE；**停用**不删切点、不改历史展示。新上传变更后若档案已停用 → `ECM_AFTER_MATERIAL_UNKNOWN`（只认现网工艺还能引用的材料）。

SOP 把投产 `material` 改掉、该号上 **还有切点**：解析器仍从新工艺列叠旧 `after_material`（会乱）。**禁止再切**（第 2 刀）；必须先回滚删掉该号旧切点，再按新投产字重新切。见 [02-upload-gates.md](02-upload-gates.md) §4.4。

| 对象 | 规则 |
|------|------|
| 工艺行 | 有切点则删挡；禁止 CASCADE 切点。IntegrityError 走现网引用保护，不改冲压删挡文案 |
| 改图后 AA | 到期不删行；切点仍叠 AA。新号 AB 另有抄来的切点行，不是孤儿 |
| 钢材 / 零件价 | 不 FK 切点；回滚后快照故意留下 |
| 失败头 `upload_file_id` | 非空则文件行必须先在 |
| pending 头 | 不得占成功版本 UNIQUE |

---

## 6. 当月材料（只在 `resolve_material`）

普通件 `material` = 工艺列再叠该身份生效月 ≤ as_of 的 `after_material`。无切点 = 工艺列。拼焊 / 利废 / 副产品不叠，仍是投产列。料厚不叠。

**禁止写回表。** 禁止在 `list_with_processes` 的返回对象上改 `material`。

上传门禁「变更前」= 对该件调 `resolve_material`（该月、不含本本）。第 4 刀批量调用同一函数，见 [04-steel-and-part-cost.md](04-steel-and-part-cost.md)。不要第二套解析器。

本刀单测：无切点=工艺字；一刀前后月；两刀排队。不要测钢价公式。

---

## 7. 本刀验收

- [ ] 工艺表不增行、不改 `material`、不改生失效四列
- [ ] 切点行能读出 `change_version` + 生效月 + `before_thickness` / `after_thickness`；有效止由下一刀推出，不落失效列
- [ ] 115AA 插一刀后解析 2025-05=DC01、2025-06=DC03（最新是 DC03，工艺列仍 DC01）
- [ ] 再插 `MAT-202507` 后：2025-06=DC03、2025-07=DC01；第二刀 before 必须是 DC03
- [ ] 同月或更早月第二刀 UNIQUE 拒
- [ ] 有切点时删工艺 IntegrityError（不改冲压删挡文案）
- [ ] 成功头 UNIQUE 含冲压工厂：振华 `MAT-202506` 不挡全鑫同项目同月同版本
- [ ] SOP 再导更新同行，`stamping_parts.id` 不变；切点 `copied_from_order_id` 可空
