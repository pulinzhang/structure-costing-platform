# 年度零件价导入模板

> **已落地。** 价表产品见 [bom-annual-part-prices-design.md](bom-annual-part-prices-design.md)。  
> 核价叶子取价：[assembly-costing-design.md](../costing/assembly-costing-design.md) §5.3（先当月冲压价表零件号，没有再年度价）。

| 文件 | 职责 |
|------|------|
| `importing.service.build_template` | 校验、按基地+项目扫 BOM / 工艺库 / 采购对象、拼文件名 |
| `template_source` | 哪些叶子进模板（去重、零价、标签） |
| `template_builder` | 行 → xlsx；不查库；第二页填写说明 |
| Parser `HEADER_*` | 表头唯一来源；只读第一张工作表 |

`GET /template?location=&vehicle_model=&year=` → 流式下载。`year` 只进文件名和上传写价表，**不参与取数**。价表仍无车型列。

下载后的 xlsx **不改一行** 即可再导入（单价允许 0）。

---

## 范围（写死）

**基地 + 项目**（`location` + `vehicle_model`）下全部 `bom_snapshots`（各 BOM 版本并集）。无 snapshot → 「请先上传该基地该项目的材料清单」。

不按「BOM 看起来像冲压」（`make` / 料厚 / 制造类别）排除。核价也不按这个认冲压件，只看当月 `stamping_part_costs` 有没有该零件号。工艺库没有的板料（如 T13J 的 `551001133AA`）必须能进模板，否则年度价导不进去、核价只能 `missing`。

只取采购对象 `other_leaf` 会漏分总成下的 L2（螺母、未进工艺库的板料）。

---

## 行源（两类并集，零件号去重）

无子件才进模板。有子件（供货总成 / 分总成）**否**：预填 0 会一口价剪枝。

| 来源 | 进模板 |
|------|--------|
| 该基地+项目采购对象 `section=other_leaf`（标准件、胶等） | **是**（即使同号也在工艺库里） |
| 该基地+项目 BOM 无子件，且零件号 **不在** 该基地+项目 `stamping_parts` | **是**（外购，含未进工艺库的 L2 板料） |
| BOM 无子件，但零件号在该项目工艺库 | **否**（走冲压零件价） |
| 有子件 | **否** |

采购对象未生成时，第一类为空，仍按第二类出模板。

去重：零件号；snapshot 按版本→id（不沿用 Repository 的新→旧），节点按 Excel 行号→id，**先出现的保留**。不把已不在当前树上的采购对象补进模板。零行 → 「没有需填年度价的外购叶子」。

| 列 | 写入 |
|----|------|
| 零件号 / 名称 | 抄当前树上的节点 |
| 规格 | 抄 `thickness_text`，空则空 |
| 采购单位 | 与「单位」相同（`qty_unit`，空或 `PCS` → `pcs`） |
| 采购单价 | **空**（不要写 0） |
| 转换系数 | **`1`**（>0，最多 6 位小数；模板按库值写，不补零） |
| 单位 | BOM `qty_unit`（核价单位） |
| 单价 | 固定 `0.0000`（Decimal，不经 float） |
| 原供货类型 | **按行**：名称含「胶」→ `胶块`；采购对象 other_leaf 或名称含螺母/螺栓等 → `标准件`；其余未进工艺库叶子 → `沿用` |
| 供应商 / 备注 | 空；**不抄**节点 remark |
| 基地 / 项目 / 年度 | **不进 Excel**（表单传入；上传仍只写基地+年） |

核价单价 = 采购单价 ÷ 转换系数。转换系数 > 0，最多 6 位小数（1 采购单位 = N 核价单位；1 英寸=25.4 mm 则填 25.4）。展示与模板不强制补齐小数位。有采购单价且「单价」为 0/空时用派生值覆盖。

---

## 工作簿

第一页表名 `年度零件价`；表头=Parser `HEADER_*`；冻结 `A2`。  
第二页 `填写说明`（换算与原因）；Parser **只读第一页**。  
空 `rows` 仍出表头，拒单在 Service。  
文件名：`年度零件价导入模板_{location}_{vehicle_model}_{year}.xlsx`。

与 `export/service.py`：列表导出另含基地/年份/审核与审计列，但核心列与本模板同契约，可再导入（基地/年度以上传页为准）。

回归：`tests/bom/test_annual_part_price_template.py`、`tests/bom/test_annual_part_price_parser.py`。
