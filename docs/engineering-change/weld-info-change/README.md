# 焊信变更 — 设计

> 状态：**设计定稿，未落地。**
> 对人说 **焊信变更**（与「设计变更」「材料变更」并列）。对象是拆解节点 `bom_welding_process_breakdown_node` 上的焊信（`weld_info_raw`）。与 `bom_welding_process_breakdown_line` 无关。
> 维护入口挂在工程变更下。记录是焊接工艺拆解的一张辅助表 **`bom_welding_process_change_info`**：用户手工指定的一整段新焊信，或停止焊信。工程变更不另建业务表。
> 抄焊接费时，节点落在某条已通过记录的开始与结束之间，就按这条焊信实时算；否则抄 SOP 年账。
> 设计变更见 [设计变更](../design-change/README.md)。材料变更见 [材料变更](../material-change/README.md)。拆解见 [焊接工艺拆解](../../bom/welding-process-breakdown-design.md)。年账见 [焊接费](../../bom/welding-fee-design.md)。

---

## 0. 一句话

焊信很少改。节点上的投产焊信、拆解明细、已经算好的 SOP 年账都保持不动。变更只记在 `bom_welding_process_change_info`：开始、结束，外加两种内容之一——用户手工写下的一整段新焊信，或停止焊信。抄焊接费时带上月份；这个节点有这样一条已通过记录，并且这个月落在开始与结束之间，就按这条记录实时算。没有这种记录，或者不带月份，就抄 SOP 年账。

常见例子：SOP 焊信里有电泳，过几个月用户写一段不含电泳的新焊信。若整段焊信都不要了，就记停止焊信，该月工艺费为 0。

---

## 1. 为什么单独立项

| 现有通道 | 它回答的事 | 焊信变化对不上的原因 |
|----------|------------|----------------------|
| 树的生失效 | 这棵总成这个月还在不在 | 截断树会把仍在供货的零件从冲压、结构、采购里一起拿掉 |
| 设计变更 | 互换性变了，换成新零件号 | 停电泳通常不换号。新树的拆解是从旧树整套抄的，节点焊信还是旧的 |
| 材料变更 | 同号、只改材料 | 焊信不是材料 |
| 焊接费年账 | 拆解明细 × 该年单价，一年一行 | 单件费用会抄进每一个月。年中焊信变了，各月仍抄到投产那一笔 |
| 拆解明细 | SOP 原文拆出来的过程量 | 焊信变更不改这些行，也不以这些行为底稿 |

协议价年内分段已否决，见 [effective-period-design.md](../../costing/effective-period-design.md)。单价仍是一年一档。`bom_welding_fees` 不加月，唯一键仍是年 + 基地 + 项目 + 拆解节点。

---

## 2. 谁记、谁读

```text
工程变更 · 焊信变更页（只做入口）
        │  调用焊接工艺拆解写入
        ▼
bom_welding_process_change_info
  挂在 bom_welding_process_breakdown_node
  开始、结束
  指定新焊信（用户手写的全文）或 停止焊信
        │
        ▼
抄焊接费（总成月核价，以及焊接费列表选了月）
        │  该节点有已通过记录，且账期月在开始与结束之间
        │      指定新焊信 → 用这段焊信全文实时解析并计价，不写回年账，不写明细
        │      停止焊信   → 工艺费 = 0
        │  否则
        │      → 抄已落库的 SOP 年账
```

| 谁 | 做 | 不做 |
|----|----|------|
| 工程变更页 | 录入、审核、删除。写入调用拆解 | 自己建业务表；改节点 `weld_info_raw`；改材料清单焊信；改树的生失效；改拆解明细 |
| 焊接工艺拆解 | 一张 `bom_welding_process_change_info`；节点被删时挡住 | import 工程变更；在拆解主表或明细上加开始、结束 |
| 焊接费 | 抄费时认出这种节点，按新焊信或停止实时算 | 把实时算的结果写进 `bom_welding_fees` 或 `bom_welding_process_breakdown_line`；给年账加 `month` |
| 总成核价 | 抄费时把本次年月交给焊接费 | 自己读 `bom_welding_process_change_info`；把下级焊接费加进总成 |

工程变更调用拆解；拆解、焊接费、总成核价不 import 工程变更。总成核价只调焊接费的抄费。

---

## 3. 表

只有一张辅助表，挂在拆解**节点**上。不挂明细，不引用 `bom_welding_process_breakdown_line`。

```text
bom_welding_process_breakdown_node     现网 SOP 节点（weld_info_raw 仍是投产焊信）
 └── bom_welding_process_change_info   这一段的新焊信，或停止焊信
```

`bom_welding_process_breakdown_line` 仍只服务于 SOP 拆解和 SOP 年账。焊信变更不插入、不更新、不删除这些行。

模型放在 `app/models/bom/`，与 `welding_process_breakdown.py` 并列。写入在 `app/services/bom/welding_process_breakdown/`。

### 3.1 `bom_welding_process_change_info`

挂 `breakdown_node_id` → `bom_welding_process_breakdown_node.id`，`ondelete="RESTRICT"`。节点上还有记录时，拆解不能删、整包生成不能清掉该节点。

| 列 | 对人说法 | 规则 |
|----|----------|------|
| `breakdown_node_id` | 哪一条拆解节点 | 必填 |
| `start_year` / `start_month` | 开始 | 必填。含本月 |
| `end_year` / `end_month` | 结束 | 同空或同有。空 = 未结束，一直用到这棵树自己到期。有则含本月，且不得早于开始 |
| `change_type` | 指定新焊信 / 停止焊信 | `specify` 或 `stop` |
| `weld_info` | 新焊信全文 | `specify` 时必填，用户手工写下的一整段，不是在旧文上改几个字的增量。`stop` 时必须为空 |
| `remark` | 原因 | 可空。例如「取消电泳」 |
| 审核 | 审核状态 | 与拆解节点同一套：待审 / 已通过，以及审核、反审核人和意见 |

`weld_info` 与节点上的 `weld_info_raw` 同级：都是焊信原文。节点那一格继续代表投产。这一列只在开始到结束之间代替它。

基地、项目、零件号、层级不在本表再存一份，列表 join 拆解节点。

硬唯一：`(breakdown_node_id, start_year, start_month)`。同一节点不能有两段从同一个月开始。跨月重叠靠 Service 挡住。

开始、结束都写在这一行上。后一段不回写前一段的结束。

---

## 4. 写入

页面上选一条已有拆解节点，再填开始、结束，并二选一：

| 选择 | 用户做什么 |
|------|------------|
| 指定新焊信 | 手工写下这一段要使用的焊信全文。页面可以带出节点上现有的 `weld_info_raw` 供改，保存的是用户确认后的全文 |
| 停止焊信 | 不填焊信。这一段没有焊信 |

保存为待审。落库只写 `bom_welding_process_change_info`。

1. 拆解节点必须在，且 `source_node_id` 能走到 L0 树根。走不到则拒绝。
2. 开始年月必填，月 1–12。结束同空或同有；有则不得早于开始。
3. 开始到结束整段落在该树根的寿命里。树根该月不存在，不能把这段写进该月。结束空着时，抄费仍先问树根：树已经到期的月不用这段。
4. 同一节点已有记录与本段有任一重叠月 → 拒绝。相邻可以：上一段结束在 6 月，下一段开始在 7 月。
5. `specify` 的 `weld_info` 去空白后不得为空。`stop` 的 `weld_info` 必须为空。
6. 已通过的记录要改开始、结束、类型或焊信全文，先反审核。反审核后，已落的月账金额不动；下次重算该月才按新内容或按 SOP。
7. 待审记录不参与抄费。抄费时把它当成没有这段。

删除一条记录只删这一行。其它段不动。已经抄进月账的金额不改。下次重算该月时，这段没了就回到 SOP 年账。

总成格子是财务认的那一笔。电泳写在总成焊信上，记录就加在总成这个拆解节点上。下级节点自己的焊信要变，在下级节点上另加一条。

---

## 5. 抄焊接费

实时算发生在抄费这一下，不另做一张月账，也不把解析结果写入拆解明细。焊接费在 `app/services/bom/welding_fee/resolve.py` 提供 `resolve_fees`，总成月核价和「选了月的焊接费列表」都调它。

入参：`year`、`location`、`vehicle_model`，以及本次要抄的 `month`。节点范围与现网抄费相同。

先看这个拆解节点在 `bom_welding_process_change_info` 里有没有**已通过**的记录，并且

```text
开始 <= 账期月 <= 结束
```

结束空着时，只要账期月不早于开始，且该月这棵树仍在，就算落在里面。一个月最多落进一条。待审记录忽略。

| 这个节点 | 抄到的金额 | 来源标记 |
|----------|------------|----------|
| 没有覆盖这个月的已通过记录 | SOP 年账 `final_welding_fee`（空则 `total_welding_fee`） | `sop` |
| 有，且 `change_type = stop` | 工艺费 = 0 | `stop`，带上记录 id |
| 有，且 `change_type = specify` | 用该行 `weld_info` 实时算 | `specify`，带上记录 id |

未传月份时（焊接费列表不选月）不读这张表，直接抄 SOP 年账。

指定新焊信的实时算：把 `weld_info` 交给现有焊接拆解 Parser，得到临时过程量，再套年账同一公式。临时过程量不落 `bom_welding_process_breakdown_line`。

```text
Parser(weld_info) → 临时工艺项
对每一项：
  标准工艺未就绪 → 本项不计
  该年该基地价表无此标准工艺名 → 本项不计，记 missing_price
  否则 line_fee = 计费用量 × 该年单价
工艺费 = Σ line_fee
其它费用 = SOP 年账上的 other_fee；没有年账行则 0
最终费用 = 工艺费 + 其它费用
```

停止焊信：工艺费 = 0，其它费用仍取 SOP 年账上的 `other_fee`（没有年账行则 0）。最终费用 = 其它费用。

计费用量仍走 `app/common/bom/welding_billing_qty.py`，辅助量优先，不乘装配用量。单价仍是 `bom_welding_unit_price`（基地 + 年 + 标准工艺名）。2026 年 7 月用 2026 年价表乘这段新焊信。

实时算不 insert、不 update `bom_welding_fees`，也不写拆解明细。没有这种记录、也没有 SOP 年账行：金额 0。有「指定新焊信」但还没有 SOP 年账行：仍按新焊信实时算，其它费用为 0。

`calc_status` 与年账相同：有未匹配或少单价为 partial，调用方照现网抄数并标缺价。停止焊信的工艺费为 0，不算缺价。

### 5.1 焊接费列表

`#/bom-welding-fee-list` 增加可选月份。年仍是现网那一格。只传月、不传年 → 422。

不选月：列表就是现在的 SOP 年账，不读 `bom_welding_process_change_info`。

选了月：落在开始与结束之间的节点，金额改为实时算的结果，并标上记录 id 和类型（指定新焊信 / 停止焊信）。其它节点仍是 SOP 年账。导出跟列表筛选，带了月就导出该月抄到的数，文件名或表头带上这个月。

年度计算页 `#/bom-welding-fee-calc` 仍只传年 + 基地 + 项目，写出的仍是 SOP 年账。它继续只读拆解明细，不读焊信变更。

### 5.2 月度核算抄费

总成月核价入参里已经有年、月。准备焊接费时调用 `resolve_fees`，把本次账期月传进去。节点落在某条已通过记录里，这一笔用实时算的结果；其它节点抄 SOP 年账。抄到卡上的仍是该节点自己的一笔，下级不累加。

| 卡上已有 | 本设计 |
|----------|--------|
| `welding_amount` | 这种节点抄实时算的最终费用；其它节点抄 SOP。无行仍是 0 |
| `welding_fee_id` | 仍指向 SOP 年账行（有则写，无则空） |
| `welding_summary` | 实时算时写明开始、结束，以及「指定新焊信」或「停止焊信」 |
| 新增 `weld_change_id` | 可空。实时算时写下 `bom_welding_process_change_info.id`。不建外键，与现网 `welding_fee_id` 一样只作溯源 |

外购总成一口价已含工费时，④⑤ 仍为 0，不因为有焊信变更再去抄焊。

已经审核落账的旧月不因新插入或删除记录而改写。下次重算该月才按当时的记录出数。

引擎里的年度补焊仍只补 SOP 年账，不传月。月度总成步骤抄费时月已经在账期里，走 §5.2。

---

## 6. 页面与 API

变化少，不做 Excel 上传。侧栏工程变更下增加分组，与设计变更、材料变更并列。一个页面：列表加录入。

| 项 | 值 |
|----|----|
| 分组 | `menu:engineering-change-weld-info-group`，文案「焊信变更」 |
| 页面 | `menu:engineering-change-weld-info`，`#/engineering-change-weld-info` |
| 前端 | `static/js/features/engineering-change/weld-info-change/` |
| API | `/api/engineering-change/weld-info` |
| 代码 | 页与路由在工程变更。写入调 `app/services/bom/welding_process_breakdown/`。表是 `bom_welding_process_change_info` |

操作码：`view`（列表、详情）、`create`、`update`、`delete`、`approve`、`reverse`。不复用设计变更或材料变更的码。新建用户不默认授予。已有设计变更菜单的用户不自动补本组。

| 方法 | 路径 | 作用 |
|------|------|------|
| GET | ``/`` | 分页列表。筛基地、项目、零件号、审核状态。`page` + `size` |
| POST | ``/`` | 新建一条。指定新焊信或停止焊信 |
| GET | ``/{change_id:int}`` | 详情 |
| PUT | ``/{change_id:int}`` | 改开始、结束、类型、焊信全文。已通过则拒绝 |
| DELETE | ``/{change_id:int}`` | 删除这一条 |
| POST | ``/{change_id:int}/approve`` | 审核通过。意见可空与否跟拆解列表现网 |
| POST | ``/{change_id:int}/reverse`` | 反审核。原因必填 |

整数路径写成 `/{change_id:int}`。静态路径若以后要加，与本 router 放一起且写在参数路径之前。

列表列：基地、项目、树根版本字、零件号、层级、开始、结束（空显示「未结束」）、类型（指定新焊信 / 停止焊信）、焊信全文、审核状态。开始、结束展示用现网 `fmtPeriod`。

---

## 7. 和设计变更、拆解生成的关系

设计变更种新树时，仍只把旧树 SOP 拆解（主表 + 全部明细）抄到新节点，不抄 `bom_welding_process_change_info`，也不按新焊信重拆。新号若从某月起要换焊信或停止焊信，在新拆解节点上另记一条。旧节点上的记录只回答旧树命中的月份。

完成停止只让旧树到期，不删焊信变更。树根已到期的月，抄费时这段不再命中。

同一零件、同一月既换号又记焊信变更：旧节点上的结束不得晚于旧树失效月；新节点上的开始不得早于新树生效月。两件事各记各的节点。

SOP 再生成、批量删除拆解：节点上仍有 `bom_welding_process_change_info` → 拒绝，文案说明先删焊信变更。与「仍被焊接费引用」同一纪律，两句分开，不要合成一句。生成与重拆都不读取、不覆盖这张表，也不改已经落库的拆解明细。

采购对象上的「特殊工艺 / 电泳」本期仍读材料清单焊信原文。本设计只改焊接费的抄数。

---

## 8. 举例

某总成节点投产焊信是「凸焊：4；电泳黑漆：0.098m2」。SOP 拆解明细有对应两行。2026 年价表都有。年账已算，含这两行，其它费用为空。

2026 年 7 月起取消电泳。在该总成节点上加一条 `bom_welding_process_change_info`：开始 2026 年 7 月，结束空，类型为指定新焊信，`weld_info` 为用户写下的「凸焊：4」。审核通过。节点 `weld_info_raw`、拆解明细、SOP 年账都不变。

| 谁在看 | 月份 | 结果 |
|--------|------|------|
| 焊接费列表 | 不选 | SOP 年账（凸焊 + 电泳） |
| 焊接费列表 / 总成核价 | 2026 年 3 月 | 3 月早于开始，抄 SOP |
| 焊接费列表 / 总成核价 | 2026 年 7 月 | 落在开始与结束之间。用「凸焊：4」实时解析并计价，只乘凸焊。年账与明细都不变。卡上 `weld_change_id` 指向这条记录 |
| 这条仍待审 | 2026 年 7 月 | 抄 SOP |
| 若类型改为停止焊信 | 2026 年 7 月 | 工艺费 0 |
| 删掉这条后再重算 7 月 | 2026 年 7 月 | 回到 SOP。已审核未重算的 7 月账保持原抄数 |

2027 年仍用「凸焊：4」：结束空着，2027 年 1 月用 2027 年单价乘这段新焊信。若 2027 年又要电泳，另记一条从 2027 年某月开始，焊信全文写回含电泳的那一句；前一条的结束写到新一条的前一个月。两段不能重叠。

---

## 9. 做 / 不做

| 做 | 不做 |
|----|------|
| 一张 `bom_welding_process_change_info`，挂在拆解节点上 | 改 `bom_welding_process_breakdown_line`；另做工艺行子表 |
| 内容是用户手工指定的一整段新焊信，或停止焊信 | 在旧明细上删一行电泳来充当变更；回写节点 `weld_info_raw` |
| 结束可空，表示未结束 | 插入下一条时回写上一条的结束 |
| 抄费时，这种节点且月份落在开始与结束之间就实时算 | 给 `bom_welding_fees` 加 `month`；实时算写回年账或写回明细 |
| 不选月、或节点没有落在段内的记录，抄 SOP 年账 | 总成核价自己读这张表 |
| 记录单独审核；待审等于没有这段 | 未审记录参与实时算 |
| 焊信写在哪个节点，记录就挂在哪个节点 | 用下级记录去改总成那一笔 |
| 设变仍只抄 SOP 拆解 | 设变自动把焊信变更抄到新号 |

---

## 10. 落地时改动的邻文档（实现时再改代码）

| 文档 | 补一句 |
|------|--------|
| [welding-fee-design.md](../../bom/welding-fee-design.md) | 年账仍不加月。列表可选月、抄费遇 `bom_welding_process_change_info` 则按新焊信或停止实时算 |
| [welding-process-breakdown-design.md](../../bom/welding-process-breakdown-design.md) | 节点可挂 `bom_welding_process_change_info`；与明细无关；有记录则禁止删节点 |
| [assembly-costing-design.md](../../costing/assembly-costing-design.md) | 抄 ④⑤ 时传账期月；命中则用实时算的金额，并记 `weld_change_id` |
| [part-number-revision-design.md](../design-change/part-number-revision-design.md) | 抄拆解仍只抄 SOP 主表和明细，不抄 `bom_welding_process_change_info` |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-10-13 | 初稿。焊信变更作为工程变更下的第三种通道：区间挂在拆解节点上，月账与列表按月取数，不改 SOP 年账。 |
| 2026-10-13 | 记录改为焊接工艺拆解的辅助表（开始、结束 + 工艺行）。抄焊接费时，这种节点落在开始与结束之间就实时算。 |
| 2026-10-13 | 表定为 `bom_welding_process_change_info`。只针对节点焊信：用户手工指定的新焊信，或停止焊信。与拆解明细无关。 |
