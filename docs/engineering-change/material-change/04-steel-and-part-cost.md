# 材料变更 — 4 一个接口（取材质）

> 落地：冲压新增 **`list_materials_as_of`**。钢材联动 Step1、零件单价 prepare **都只调它**。不改 `list_with_processes`，不改 `list_material_specs` 现网签名，不改零件价 `grade == material` 那一行。  
> 契约：[00-contract.md](00-contract.md)　目录：[README.md](README.md)

当月材料只在冲压域：`list_materials_as_of` 读 `stamping_part_material_changes`，把生效月不晚于账期的最后一刀 `after_material` 叠到工艺列上。门禁向冲压要同一结果。冲压不 import 材料变更。

---

## 对照现网

| | 钢材联动 Step1 | 零件单价 |
|---|---|---|
| 现网 | `list_material_specs(location)`：整基地，不过生失效，主表 ∪ 拼焊子片，SQL 去重。不传年月 | `list_with_processes(location, vehicle_model, as_of)` 之后读工艺列 `material` |
| 本刀 | 改调 `list_materials_as_of(location, year, month)` | 零件身仍 `list_with_processes`。材质改从同一接口按 `part_id` 取 |

`list_with_processes` 还被加工费（`overlap_year`）、就绪计数用。本刀不改它，不在返回的 `StampingPart` 上改 `material`。

`list_material_specs(location)` 保持现网，无年月。仪表盘 `count_material_specs` / `list_distinct_spec_grades` 继续走这条 UNION。钢材 Step1 不再调它。

相对现网钢材：只留下该月 `period_hit` 仍有效的件。过期件不再进入当月规格。期间钥匙与零件价相同。

---

## 接口

`StampingPartService.list_materials_as_of(location, year, month, vehicle_model=None)`

```
不传 vehicle_model → 整基地（钢材）
传 vehicle_model   → 该项目（零件价）
期间               → 与 list_with_processes 的 as_of 同一条 period_hit
```

返回行：`part_id`、`location`、`material`、`thickness`、`blank_id`（空 = 零件行，有值 = 拼焊子片行）。

| 件 | material | thickness |
|---|---|---|
| 普通件 | 工艺列再叠冲压历史（无历史 = 工艺列） | 工艺 `thickness`，不叠 |
| 拼焊子片 | 子片列（本通道不切拼焊）。总成该月无效则不带 | 子片列 |
| 利废 / 副产品 | 工艺列，不叠 | 工艺列 |

空材料、空料厚也返回。零件价仍走「材质为空」。钢材 Step1 丢掉空材料、空料厚，再按 `(location, material, thickness)` 去重（现有 Python 去重留在 `load_materials.py`）。

只返回行。禁止给 session 里的 `StampingPart.material` 赋值，禁止 flush/commit 回工艺表。不加载工序。

冲压自己读历史表。不在启动时绑定下游函数。核价代码只出现 `list_materials_as_of(...)`。

---

## 调用

- `load_materials.py`：`list_materials_as_of(location, request.year, request.month)`。
- 零件价 prepare：尺寸和工序仍 `list_with_processes`。普通件用本接口 `blank_id` 为空的那一行 `material` 做现有 `grade == material`。拼焊仍读子片列。

禁止：改 `list_with_processes` 叠材料；给 `list_material_specs` 加年月；costing 自己查切点表；新开规格 HTTP；改 `GET /materials`（那条走 `list_parts_for_materials`）；改核价引擎公式；改模具布点的 `die_repo.list_with_processes`。
