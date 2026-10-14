# 焊信变更 · 抄焊接费 — 设计

> 状态：**设计定稿，未落地。**
> 本篇只写抄数。记录从哪来、怎么审，见 [`bom_welding_process_change_info`](bom-welding-process-change-info-design.md)。目录见 [焊信变更](README.md)。
> 年账见 [焊接费](../../bom/welding-fee-design.md)。`bom_welding_fees` 不加月，唯一键仍是年 + 基地 + 项目 + 拆解节点。
> 焊接费在 `app/services/bom/welding_fee/resolve.py` 提供 `resolve_fees`。总成月核价和「选了月的焊接费列表」都调它。

---

## 0. 一句话

抄焊接费时带上月份。这个节点在 `bom_welding_process_change_info` 里有一条已通过记录，并且这个月落在开始与结束之间，工艺费就抄头上的 `welding_fee`，不写回年账，不写拆解明细。没有这种记录，或者不带月份，就抄 SOP 年账。

有焊信时，工艺费抄头上已经算好的 `welding_fee`。无焊信时头上该数已是 0。

---

## 1. 谁读

```text
bom_welding_process_change_info（只读已通过行）
        │
        ▼
resolve_fees(year, location, vehicle_model, month)
        │
        ├── 焊接费列表（选了月）
        └── 总成月核价（把本次年月交进来）
```

| 谁 | 做 | 不做 |
|----|----|------|
| 焊接费 | 抄费时认出这种节点，工艺费用头上的 `welding_fee` | 把抄到的结果写进 `bom_welding_fees` 或 `bom_welding_process_breakdown_line`；给年账加 `month`；重算焊信变更的金额；调用 Parser |
| 总成核价 | 抄费时把本次年月交给焊接费 | 自己读 `bom_welding_process_change_info`；把下级焊接费加进总成 |

焊接费、总成核价不 import 工程变更。

协议价年内分段已否决，见 [effective-period-design.md](../../costing/effective-period-design.md)。单价仍是一年一档。

---

## 2. 抄费

抄费发生在这一下，不另做一张月账。命中焊信变更时不再重算金额，也不把结果写入拆解明细。

入参：`year`、`location`、`vehicle_model`，以及本次要抄的 `month`。节点范围与现网抄费相同。

先看这个拆解节点在 `bom_welding_process_change_info` 里有没有**已通过**的记录，并且

```text
开始 <= 账期月 <= 结束
```

结束空着时，只要账期月不早于开始，且该月这棵树仍在，就算落在里面。一个月最多落进一条。待审记录忽略。

| 这个节点 | 抄到的金额 | 来源标记 |
|----------|------------|----------|
| 没有覆盖这个月的已通过记录 | SOP 年账 `final_welding_fee`（空则 `total_welding_fee`） | `sop` |
| 有，且头上 `has_weld_info` 为假 | 工艺费 = 头上的 `welding_fee`（已是 0） | 无焊信，带上头 id |
| 有，且头上 `has_weld_info` 为真 | 工艺费 = 头上的 `welding_fee`（已是明细金额之和） | 选中的单价，带上头 id |

未传月份时（焊接费列表不选月）不读这张表，直接抄 SOP 年账。

命中已通过的头时，工艺费直接用头上的 `welding_fee`，不再解析焊信，也不再按账期年重乘单价。数量和单价已经在保存变更时写进明细。

```text
工艺费 = 头上的 welding_fee
其它费用 = SOP 年账上的 other_fee；没有年账行则 0
最终费用 = 工艺费 + 其它费用
```

无焊信时工艺费已经是 0。其它费用仍取 SOP 年账上的 `other_fee`（没有年账行则 0）。最终费用 = 其它费用。

这条路径不走 `welding_billing_qty`，也不调用 Parser。SOP 年账那条仍按现网公式。

抄费不 insert、不 update `bom_welding_fees`，也不写拆解明细，也不改焊信变更的金额。没有这种记录、也没有 SOP 年账行：金额 0。有焊信变更但还没有 SOP 年账行：工艺费仍用头上的 `welding_fee`，其它费用为 0。

命中焊信变更时，工艺费以头上已算好的数为准，不因为单价表后来改价而标缺价。无焊信的工艺费为 0，不算缺价。SOP 年账那条仍按现网 `calc_status`。

---

## 3. 焊接费列表

`#/bom-welding-fee-list` 增加可选月份。年仍是现网那一格。只传月、不传年 → 422。

不选月：列表就是现在的 SOP 年账，不读 `bom_welding_process_change_info`。

选了月：落在开始与结束之间的节点，工艺费改为头上的 `welding_fee`，并标上头 id，以及各条单价或「无焊信」。其它节点仍是 SOP 年账。导出跟列表筛选，带了月就导出该月抄到的数，文件名或表头带上这个月。

年度计算页 `#/bom-welding-fee-calc` 仍只传年 + 基地 + 项目，写出的仍是 SOP 年账。它继续只读拆解明细，不读焊信变更。

---

## 4. 月度核算抄费

总成月核价入参里已经有年、月。准备焊接费时调用 `resolve_fees`，把本次账期月传进去。节点落在某条已通过记录里，这一笔用实时算的结果；其它节点抄 SOP 年账。抄到卡上的仍是该节点自己的一笔，下级不累加。

| 卡上已有 | 本设计 |
|----------|--------|
| `welding_amount` | 这种节点抄实时算的最终费用；其它节点抄 SOP。无行仍是 0 |
| `welding_fee_id` | 仍指向 SOP 年账行（有则写，无则空） |
| `welding_summary` | 命中时写明开始、结束，以及各条单价项目或「无焊信」 |
| 新增 `weld_change_id` | 可空。实时算时写下 `bom_welding_process_change_info.id`。不建外键，与现网 `welding_fee_id` 一样只作溯源 |

外购总成一口价已含工费时，④⑤ 仍为 0，不因为有焊信变更再去抄焊。

已经审核落账的旧月不因新插入或删除记录而改写。下次重算该月才按当时的记录出数。

引擎里的年度补焊仍只补 SOP 年账，不传月。月度总成步骤抄费时月已经在账期里，走本节。

---

## 5. 举例

记录怎么记，见 [记录表举例](bom-welding-process-change-info-design.md)。下面用同一条：总成节点上一条已通过的头，开始 2026 年 7 月，结束空，`has_weld_info` 为真，头上 `welding_fee` 已是青岛 2026「凸焊」那一行的金额。SOP 年账含凸焊和电泳，其它费用为空。

| 谁在看 | 月份 | 结果 |
|--------|------|------|
| 焊接费列表 | 不选 | SOP 年账（凸焊 + 电泳） |
| 焊接费列表 / 总成核价 | 2026 年 3 月 | 3 月早于开始，抄 SOP |
| 焊接费列表 / 总成核价 | 2026 年 7 月 | 落在开始与结束之间。工艺费用头上的 `welding_fee`。年账与拆解明细都不变。卡上 `weld_change_id` 指向这条头 |
| 这条仍待审 | 2026 年 7 月 | 抄 SOP |
| 若改为无焊信 | 2026 年 7 月 | 工艺费 0 |
| 删掉这条后再重算 7 月 | 2026 年 7 月 | 回到 SOP。已审核未重算的 7 月账保持原抄数 |

2027 年这段结束仍空：2027 年 1 月仍抄头上已算好的 `welding_fee`，不改用 2027 年单价。要换 2027 年的价，另记一条开始年是 2027 的头。

---

## 6. 做 / 不做

| 做 | 不做 |
|----|------|
| 抄费时，这种节点且月份落在开始与结束之间就实时算 | 给 `bom_welding_fees` 加 `month`；实时算写回年账或写回明细 |
| 不选月、或节点没有落在段内的记录，抄 SOP 年账 | 总成核价自己读 `bom_welding_process_change_info` |
| 待审记录忽略 | 未审记录参与实时算 |
| 无焊信的工艺费为 0，其它费用仍取 SOP 年账 `other_fee` | 无焊信把其它费用也清成 0 |
| 年度计算页仍只写 SOP 年账 | 年度计算页读取焊信变更 |

---

## 7. 落地时改动的邻文档（实现时再改代码）

| 文档 | 补一句 |
|------|--------|
| [welding-fee-design.md](../../bom/welding-fee-design.md) | 年账仍不加月。列表可选月、抄费遇已通过的焊信变更头时，工艺费用头上的 `welding_fee` |
| [assembly-costing-design.md](../../costing/assembly-costing-design.md) | 抄 ④⑤ 时传账期月；命中则用实时算的金额，并记 `weld_change_id` |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-10-13 | 从焊信变更稿拆出。本篇只写抄焊接费。 |
| 2026-10-13 | 记录改为：选中的焊信原文，或 `no_weld_info`。抄费按这两样读，不改写原文。 |
| 2026-10-13 | 有焊信时按变更明细逐句解析后加总。无焊信仍看头上的 `has_weld_info`。 |
| 2026-10-13 | 工艺费改抄头上已算好的 `welding_fee`。不再按账期年重乘单价。 |
