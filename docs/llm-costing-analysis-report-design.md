# 核价结果 → LLM 智能分析报告 — 设计文档

> 状态：**设计稿（不实现）**  
> 业务主体：**使用本产品的冲焊装配供应商**（向主机厂客户供货）· 主用户：**采购部**（向各类配件 / 冲压等供应商采购，支撑成品交付）· 产品可多租户售卖，文案不绑定具体公司名  
> 参考实现：`D:\hylir\backgroud\hylir-node-mcp-server`——**仅复用「预聚合 Context + 强约束 Prompt」**，不复用其 Chat/SSE 产品形态  
> 关联：`docs/costing-engine-design.md`、`docs/l0-assembly-costing-design.md`、`docs/architecture.md`  
> 原则：**不改动现有核价公式**；LLM 只消费**已落库的计算结果与可复现的聚合视图**，严禁重新算价；报告措辞面向**采购决策与议价准备**，不是写给模型工程师看的技术日志。

---

## 0. 产品约束（已冻结）

| # | 约束 | 说明 |
|---|------|------|
| C1 | **纯 REST** | 后端只提供数据 + **出具完整报告**；接口返回整份 Markdown（或等价正文），无增量推送 |
| C2 | **不做流式** | 禁止 SSE / WebSocket；前端「加载中」转圈，等任务成功后一次性渲染 |
| C3 | **对话壳；自由输入也发请求** | 主交互为对话（胶囊 + 输入框）。**凡 scope 齐全且问题非空，一律 `POST /api/llm/reports`**（含不点胶囊的自由输入）。胶囊只是快捷填参；**禁止**「无法匹配就本地拒答、不调 API」。不做的是：无 scope 闲聊、跨系统开放域、第二套对话引擎 / Tool Calling |
| C4 | **异步任务** | 生成走与现网核价相同的 **AsyncTask + 轮询**（见 §5.2）；禁止依赖调高网关超时的「长同步」作为主路径 |
| C5 | **后端无会话状态** | 每次请求自带完整 `scope` + `user_question` + `report_type`（可为 `auto`）；**不**在服务端持久化多轮对话 Session |
| C6 | **采购视角优先** | 默认受众是租户内的**采购员 / 采购主管**；技术核价口径保留，但叙述翻译成「买贵了吗 / 跟谁谈 / 缺什么价谈不了」 |
| C7 | **商号中立（可售卖）** | 设计文案、默认 Prompt、水印**不写死**具体本公司或主机厂商号；部署时可配置显示名，示例数据可用「青岛基地 / T28」等通用占位 |
| C8 | **对话历史 = localStorage** | 聊天气泡、本地 `conversation_id`、与气泡关联的 `report_id`/`task_id` **仅存浏览器 localStorage**；换机/清缓存即丢失；服务端仍可有报告落库（供审计/幂等），与前端聊天线程解耦 |
| C9 | **Schema 为字段真相** | Context Pack / Prompt 中的英文字段名、金额口径、枚举值**必须对齐现网 Pydantic VO/DTO**；禁止另造一套「分析专用字段」让模型瞎猜；中文释义从 Schema/`Field`/受控词典生成后注入 |
| C10 | **金额单位禁止「万元」** | 核价结果默认单位为 **元**（成品侧多为元/件且已含单车用量）；报告中**严禁**改写为「万元」「千元」或自行÷10000；须原样使用 JSON 数字字符串，并写明「元」 |
| C11 | **异常分析必做** | 凡 Pack 含 `missingPriceRisk` / `partial` / `calc_status!=ok` / gate 缺口，报告须有独立「异常与风险」板块；无异常则明确写「本次未见 partial/缺价」——禁止假装一切正常却漏掉 JSON 里的风险字段 |
| C12 | **数据只经现有 Service** | Context Pack 的一切业务数据，只调用 **既有上游 Service**（costing / stamping / bom / yishiyiyi / settings 等）的稳定查询 API 获取 VO；**禁止**在 `llm` 再建一套取数 Repository/SQL/「独立查询工具」直连结果表；`SchemaCatalog` 只读 Schema、不算业务数据 |
| C13 | **壳层聊天助理；不抢镜头** | 前端是**全局浮动聊天助理**，不是业务菜单页：入口为顶栏 **「使用帮助」左侧** 的标准机器人图标；点开为浮动窗（可最大化）；可收成**屏幕最右侧小气泡**。**禁止**挂侧栏/`data-page` 菜单、禁止独占 `#pageContent`、禁止开屏强弹/霓虹大按钮抢业务视线 |

**已明确不作为缺口**：慢思考流式输出、服务端多轮 Session、反馈闭环（点赞）——后二者可作 P3 锦上添花，不阻塞立项。  
对话 UX 与「无流式 / 异步整包返回」不冲突：用户发问 → 气泡显示「分析中」→ 轮询完成后助手气泡一次贴出完整 Markdown → **写入 localStorage**。

---

## 1. 业务定位：本公司 · 主机厂客户 · 供应商

### 1.1 价值链（智能体站在哪）

```text
配件 / 冲压等供应商  ──卖零件/工序──►  本公司采购部  ──冲焊装配成 L0 成品──►  主机厂客户
        ▲                                    │
        │ 议价、缺价追要、月度联动核价          │ 对内：成本是否可接受
        │                                    │ 对外：支撑对主机厂报价 / 核对
        └──────── 本智能体服务的主战场 ────────┘
```

| 关系 | 本系统里常见数据含义 | 采购关心什么 |
|------|----------------------|--------------|
| 本公司 ← 供应商 | 冲压工厂价、年度外购价、焊接单价、钢材联动价、包装运输等 | **我该付给供应商多少**；哪类成本在涨；哪家/哪号缺价 |
| 本公司 → 主机厂 | L0 供货总成 `grand_total`（月总账 + 间接） | **单车/单件交付成本底数**；涨价能否向客户传导、内部是否吃掉 |
| 本公司内部 | 核价引擎、合册 Excel、审核状态 | 数字能不能拿去开会；有没有洞（partial） |

> 智能体**不是**主机厂侧 AI，也**不是**供应商门户。默认只服务**本公司（租户）内部账号**；对外纪要需人工脱敏后再发。

### 1.2 一句话目标（业务语言）

让采购部在选定 **基地 + 年 + 月（+ 项目/BOM）** 后，一键得到一份「**本月采购成本说得清、涨跌找得到、缺价列得出、下一步找谁**」的完整分析报告——数据来自已落库核价结果，叙述面向采购工作，不替代合册对账 Excel。

### 1.3 一句话目标（技术语言）

结构化结果经「**固定报告模板 → Context Pack → 版本化 Prompt → LLM**」生成可核对、可追责、可轮询取回的 Markdown 报告（REST + AsyncTask）。

---

## 1A. 角色、关注点与报告诉求

> 同一份核价数据，不同角色问的问题不同。智能体用 **`report_type` + 可选 `audience`** 切换侧重点；**数字同源**，**板块与措辞按角色裁剪**。

### 1A.1 角色地图

| 角色代号 | 典型岗位 | 在价值链中的位置 | 核心问题（一句话） |
|----------|----------|------------------|-------------------|
| `buyer` | **采购员** | 本公司 ↔ 供应商一线 | 这个月哪些件贵了？缺哪些价？我下周该催谁、谈谁？ |
| `buyer_lead` | **采购主管 / 科长** | 采购部对内管理 | 本基地本月总成本与构成？风险清单？资源投在哪几条线？ |
| `costing` | **核价 / 成本工程师** | 公式与主数据正确性 | 口径对不对？partial 原因？主数据缺口能否硬停归因？ |
| `sales_quote` | **销售 / 报价对接** | 本公司 → 主机厂 | 成品总费用能不能支撑对客沟通？哪些 L0 是涨价敏感点？ |
| `exec` | **采购经理 / 管理层** | 决策与汇报 | 三页内说清涨跌与风险；不要工序明细 |

P0 默认受众：`buyer` + `buyer_lead`（同一 `dashboard` 报告里用板块兼顾；页眉标明「采购分析」）。  
`costing` / `sales_quote` / `exec` 通过后续模板或 `audience` 参数加深，不另起一套算价。

### 1A.2 采购员（`buyer`）——日用主角

| 关注点 | 希望报告回答 | 对应数据 / Pack | 建议动作（报告末尾可写） |
|--------|--------------|-----------------|--------------------------|
| **月度价格变动** | 同零件/同规格比上月贵了多少 | `mom_comparison`、钢材/零件 Top 涨幅 | 导出涨价清单，约谈供应商 |
| **谈价弹药** | 贵在材料、加工还是废料扣减 | `stamping_cost_summary`、钢材加减价贡献 | 带着联动价与工艺匹配记录开会 |
| **缺价 / 谈不拢** | 哪些零件号还没有有效价 | `missing_price_risk`、partial | 按零件号催供应商报价 / 补年度价 |
| **外购与一口价** | 年度价、分总成包价是否异常 | L0 五块中的 `purchased` / `bundle` | 核对年度零件价表是否过期 |
| **按工厂跟进** | 哪个冲压工厂侧更贵或更缺 | 零件价按 `stamping_supplier` 分布 | 分工厂催办任务 |
| **时效** | 报告是否基于本月已跑通核价 | `scope_meta`、engine run | 未跑通则先补主数据或跑引擎 |

**采购员反感**：满屏英文字段、让自己心算占比、把「供应商未确认类」业务说成技术失败、没有零件号样本。

### 1A.3 采购主管（`buyer_lead`）

| 关注点 | 希望报告回答 | Pack / 板块 |
|--------|--------------|-------------|
| **盘子** | 本月 L0 总费用、月总账、间接合计 | `month_overview` |
| **结构** | 冲压 / 外购 / 一口价 / 焊接 / 间接谁占大头 | 五块 + 间接汇总 |
| **头部集中度** | TopN 成品是否拖垮整车成本 | `l0_top_drivers` |
| **风险** | partial 比例、缺价是否影响对主机厂交付节奏 | `missing_price_risk` |
| **节奏** | 主数据硬停还是算价未完成 | `gate` / engine digest |
| **分工** | 材料岗 vs 外购岗 vs 焊接相关跟进什么 | 按成本块拆「责任线索」（非组织架构强绑，用成本块提示） |

### 1A.4 核价 / 成本工程师（`costing`）

| 关注点 | 报告要求 |
|--------|----------|
| 口径 | 严格区分月总账 vs 总费用；不编造比率 |
| 可追溯 | 可指向合册 / 列表页；`prompt_version` 可查 |
| 缺口 | `gate` 模板：缺基准价、政策、废料价等 → navigate |
| 审核 | 未审核数据必须标注，避免当已定稿外传 |

### 1A.5 销售 / 报价（`sales_quote`，对主机厂）

| 关注点 | 报告要求 |
|--------|----------|
| **成品视角** | 以 L0 `grand_total` 为主，少写冲压工厂内部分工 |
| **涨价解释** | 能说清「材料联动 / 焊接 / 间接」哪块动了（有 Pack 证据才写） |
| **敏感** | 默认**不**把供应商名称与议价策略写进可一键外发的摘要；完整版仅内部角色可见（权限，见 §10） |
| **非目标** | 不自动生成「给主机厂的正式报价函」；只提供内部底数解读 |

### 1A.6 管理层（`exec`）

| 关注点 | 报告要求 |
|--------|----------|
| 极短 | 结论先行：总费用环比、三大风险、三项建议 |
| 无表海 | Top5 即可；细节链到采购员报告 |
| 决策 | 「是否需要启动专项议价 / 是否阻塞某项目交付」 |

### 1A.7 角色 × 报告模板矩阵（产品主表）

| `report_type` | 主受众 | 一句话用途 | 采购场景例句 |
|---------------|--------|------------|--------------|
| `dashboard` | `buyer_lead` + `buyer` | 月度采购成本总览 | 「青岛 2025-01 T28 这个月采购成本怎么样？」 |
| `steel` | `buyer`（材料） | 钢材联动与加减价 | 「钢价联动后哪些规格在涨？跟钢厂/政策有关吗？」 |
| `stamping_part` | `buyer`（冲压件） | 冲压件采购价解读 | 「哪个工厂、哪些件材料净成本异常？」 |
| `l0` | `buyer_lead` + `sales_quote` | 成品交付成本 | 「交给主机厂的总成里，贵的是哪些？」 |
| `part_drilldown` | `buyer` | 单号议价卡 | 「就这个零件号，我怎么跟供应商谈？」 |
| `gate` | `costing` + `buyer_lead` | 为何算不出 / 谈不了 | 「主数据还缺什么，谁去上传？」 |
| `exec_brief`（P1+） | `exec` | 一页纸简报 | 「给我三分钟版。」 |

### 1A.8 报告叙述原则（所有角色共用）

1. **先结论后明细**：采购开会先看涨跌与风险，再看表。  
2. **用零件号 / 总成号说话**：便于转办供应商。  
3. **建议必须可执行**：催报价、补年度价、看钢材列表、跑引擎——对应系统跳转或明确岗位动作；禁止「加强管理」空话。  
4. **内外有别**：对内可写供应商线索；标注「内部」；不对主机厂口径自动承诺。  
5. **不做自动砍价**：智能体提供事实与问题清单，**议价策略与目标价由采购人拍板**。

---

## 2. 为什么不能「全量结果直接喂 LLM」

| 问题 | 后果 |
|------|------|
| Token 爆炸 | 单基地单月明细远超上下文 |
| 幻觉算价 | 与系统落库金额冲突 |
| 口径歧义 | 月总账 vs 总费用等 |
| 权限与审计 | 全表 dump 难授权 |
| 不可复现 | 同问异答无法验收 |

**结论**：系统侧先做 **Analysis Context Pack**（KPI / TopN / 异常样本 / 对比差分）；LLM 只解读，不算价。

---

## 3. 参考项目可复用点（hylir-node-mcp-server）

| 复用 | 不复用（本产品已否决或降级） |
|------|------------------------------|
| Context 预聚合后再调 LLM | 生产主路径的自然语言意图路由 |
| `FIELD_LABELS` / 口径强约束 Prompt | Chat 流式、Tools 多轮拉数作为主 UX |
| 低温度、禁止编造数字 | 把 MCP / 服务端会话当 P0 必交付 |

组件对标：`LlmContextAggregator`（**调上游 Service** 组装 Pack）、`SchemaCatalog`（只读 Schema）、按 `report_type` 选 Prompt。MCP 仅作 **P2+ 可选**；Tools 亦不得另建取数通道。

---

## 4. 分析内容与逻辑（年数据 · 月数据 · 核算分层）

> 智能体**不重新算价**，只解读系统已落库结果。分析必须说清：**哪些按年相对稳定、哪些按月会动、各层结果如何叠成成品总费用**。口径对齐 `docs/costing-engine-design.md`、`docs/l0-assembly-costing-design.md`。

### 4.1 一张图：从主数据到可分析结论

```text
┌─ 上传 / 配置（分析只作「缺什么」归因，不整表喂模型）─────────────┐
│ 工艺零件 · 冲次单价 · 焊接单价 · BOM · 年度零件价 · 包装运输      │
│ 钢材基准价(年月) · 加减价政策 · 废料月度价 · 系统费率            │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ 年计算所得     │     │ 月计算所得（主链）│     │ 成品月账（汇总结） │
│ 相对稳定       │     │ 每月会变         │     │ L0 月总账+间接    │
│ · 冲压加工费   │     │ · 钢材联动价     │     │ · grand_total    │
│ · 焊接工艺拆解 │     │ · 冲压零件价     │     │ · ok / partial   │
│ · L0 焊接费    │     │                 │     │                  │
└───────┬───────┘     └────────┬────────┘     └────────┬─────────┘
        │                      │                       │
        └────────── 只读聚合 Context Pack ──────────────┘
                                │
                                ▼
                     对话报告（采购语言解读）
```

**采购口述规则（写进 Prompt）：**

| 说法 | 含义 |
|------|------|
| 「今年定下来的」 | 年计算所得 + 年度上传价（外购/一口价/焊接费/包装运输等） |
| 「这个月在动的」 | 钢材联动、冲压零件价、进而拉动 L0 里的冲压分项与总费用 |
| 「交给主机厂的底数」 | L0 `grand_total`（月总账 + 间接），不是某一层中间价 |

### 4.2 年数据：内容与分析逻辑

#### 4.2.1 年度上传类（主数据，分析侧重点 = 覆盖与异常，不算过程）

| 数据 | 粒度 | 进成品账的角色 | 分析时关注 |
|------|------|----------------|------------|
| 年度零件价 | 年 + 基地 + 零件号 | L0 ②外购 / ③一口价 | 缺价、异常高价 Top；是否过期未更新 |
| 包装运输费 | 年 + 基地 + L0 零件号 | 间接 I1/I2 | 缺行（现网可记 0）、金额异常 |
| 焊接单价 | 年 + 基地 | 年焊接费计算输入 | 缺单价 → 焊接费/拆解失败归因 |
| BOM 快照 | 基地 + 项目 + BOM 版本 | 结构与用量 | 版本是否齐全、有无 L0 |

默认 **不**把年度价全表塞进 Context；只给「缺价样本 / TopN / 覆盖率」。

#### 4.2.2 年度计算所得（引擎可自动补算）

| 结果 | 表（示意） | 粒度 | 下游谁用 | 分析逻辑 |
|------|------------|------|----------|----------|
| 冲压加工费 | `stamping_process_fees` / items | 年相关 × 工厂 | 月度冲压零件价中的加工费部分 | 有无结果、工厂覆盖、异常高加工费零件 |
| 焊接工艺拆解 | `bom_welding_process_breakdown_*` | L0Scope | L0 焊接费 | 是否已生成；失败则成品焊接分项风险 |
| 成品 L0 焊接费 | `bom_l0_welding_fees` | L0Scope | L0 ④⑤ | 焊接费合计、其它费、缺价/未算清单 |

**年数据分析结论模板（给 LLM）：**

1. 本年（该基地）年度价 / 焊接费 / 加工费是否「齐套可用」。  
2. 齐套前提下，指出**金额头部**与**缺价阻塞**（零件号级）。  
3. 明确：**年数据齐不等于月成本不变**——月成本仍受钢材联动与冲压价拉动。

### 4.3 月数据：内容与分析逻辑

对话顶栏 scope 的 **年+月** 决定「分析哪个月的月链」；环比对比 **上月同 scope**。

| 结果 | 表 | 粒度 | 分析逻辑 |
|------|-----|------|----------|
| 钢材联动价 | `steel_prices` | 基地 × 年 × 月 × 规格键 | 均价/加减价贡献；环比涨幅 Top 规格；匹配失败数 |
| 废料月度价等 | 上传配置 | 年 × 月 × 基地 | 多在 `gate`：缺则整月硬停，分析解释「为何算不出」 |
| 冲压零件价 | `stamping_part_costs` | 年×月×基地×工厂×零件 | 材料净成本 vs 加工费；工厂分布；无钢材匹配；环比 |
| 成品 L0 核价 | `costing_l0_assembly_costs*` | 年×月×基地×项目×BOM×L0 | 见 §4.4；采购主结论层 |
| 引擎 Run | `costing_engine_runs` | 基地×年×月 | 本月是否跑通、硬停项、步骤失败 |

**月数据分析主线（dashboard 默认）：**

1. **完备性**：本月引擎是否成功；L0 ok vs partial。  
2. **总盘**：`grand_total` / `total_amount` / 间接合计。  
3. **结构**：五块积木 + 间接——回答「钱在哪一类」。  
4. **月动因**：相对上月，哪些 L0 / 钢材规格 / 冲压件拉动涨跌（比率后端算）。  
5. **行动**：缺价催办、钢材议价、工厂分头催。

### 4.4 核算分层：各层结果如何进入分析

智能体按**依赖链自下而上**解读，禁止跳层编造。

```text
层0  配置与上传        → 分析：缺口 / gate（谈不了的根因）
层1  年计算所得         → 分析：加工费、焊接拆解与焊接费是否齐套
层2  月·钢材联动        → 分析：材料单价变动
层3  月·冲压零件价      → 分析：单件采购成本（含材料净额+加工费等落库字段）
层4  月·成品 L0         → 分析：交付底数（汇总结论层）
```

#### 4.4.1 层2 → 层3（钢材如何影响冲压件）

- 冲压零件价计算消费当月钢材联动结果（及废料价、工艺尺寸等）。  
- 分析表述：**「材料侧」**看钢材 Pack；**「零件侧」**看 `stamping_part_costs` 的材料净成本 / 废料扣减 / 加工费分列。  
- 不得由模型用基准价自己重算吨价。

#### 4.4.2 层1+层3 → 层4（L0 五块积木 + 间接）

| L0 分项 | 主要来源时效 | 分析时应强调 |
|---------|--------------|--------------|
| ① 冲压小计 `stamping_amount` | **月**（冲压零件价） | 本月材料/加工波动的主通道 |
| ② 年度/外购 `purchased_amount` | **年**（年度零件价） | 「今年表上的价」，月环比通常不应大变，大变则查是否换 BOM/补价 |
| ③ 一口价 `bundle_amount` | **年** | 分总成包价；勿与拆散 L2 混谈 |
| ④ 焊接 `welding_amount` | **年**（L0 焊接费） | 年齐套问题；月报里变动小属正常 |
| ⑤ 焊接其它 | 按需/年 | 单独点名，避免并进④ |
| 间接 `indirect_*` | 年包装运输 + **月总账×费率** | I3～I6 随月总账水涨船高；I1/I2 偏年 |

```text
total_amount（月总账）= ①+②+③+④+⑤     ← 不含间接
grand_total（总费用）= total_amount + indirect_amount
```

**分层归因口诀（Prompt 强制）：**

- 总费用涨了 → 先看 ①是否涨（月链）→ 再看间接是否因月总账抬升 → 再看②③④是否异常（年侧不该月月跳）。  
- partial → 先列缺哪一层价（缺冲压 / 缺年度价 / 缺焊接等），再谈金额。

#### 4.4.3 各层「分析产出」对照

| 层 | 主要 Pack | 对话提问侧重（§9.3） | 采购要带走的结论 |
|----|-----------|----------------------|------------------|
| 0 配置 | `engine_gate_digest` | Q12 | 缺什么主数据、去哪上传 |
| 1 年计算 | （P1 可增 `annual_calc_digest`） | 加工费/焊接是否齐 | 年侧能否支撑月算 |
| 2 钢材 | `steel_price_summary` + `mom_comparison` | Q21～Q23 | 跟钢种/规格议价清单 |
| 3 冲压件 | `stamping_cost_summary` | Q31～Q33 | 工厂×零件催办/议价 |
| 4 成品 | `month_overview` + `l0_top_drivers` + `l0_indirect_summary` | Q01～Q05、Q41～Q43 | 交付底数、Top 总成、汇报一页纸 |
| 跨层 | `missing_price_risk`、`part_drilldown` | Q11、Q51 | 阻塞清单、单号谈价卡 |

### 4.5 结果资产表（落库索引）

| 领域 | 时效 | 落库表 | API 方向 |
|------|------|--------|----------|
| 钢材联动价 | 月 | `steel_prices` | `/api/costing/steel-price/*` |
| 冲压零件价 | 月 | `stamping_part_costs` | `/api/costing/stamping-part-cost/*` |
| 成品 L0 | 月 | `costing_l0_assembly_costs` + items/indirects | `/api/costing/l0-assembly-costs/*` |
| 冲压加工费 | 年 | `stamping_process_fees*` | `/api/stamping/process-fees/*` |
| 焊接拆解 / L0 焊接费 | 年 | `bom_welding_*` / `bom_l0_welding_fees*` | `/api/bom/...` |
| 引擎 Run | 月编排 | `costing_engine_runs` / `_steps` | `/api/costing/engine/*` |

上传类仅在归因 / `gate` 中带摘要或缺口列表。

### 4.6 Analysis Context Pack（输入侧）

| Pack ID | 主要服务层 | 内容 |
|---------|------------|------|
| `scope_meta` | 全局 | 范围、引擎 run、`hasData` |
| `engine_gate_digest` | 层0 | 硬停缺口 + navigate |
| `annual_calc_digest` | 层1（P1） | 加工费/拆解/焊接费齐套与样本 |
| `steel_price_summary` | 层2 | 钢厂/牌号、加减价贡献、环比 Top 规格 |
| `stamping_cost_summary` | 层3 | 零件价分布、TopN、匹配失败、工厂分布 |
| `month_overview` | 层4 | L0 合计、ok/partial、五块分项、间接合计 |
| `l0_top_drivers` | 层4 | TopN 总费用 / 环比涨幅、partial 列表 |
| `l0_indirect_summary` | 层4 | 间接科目汇总 |
| `missing_price_risk` | 跨层 | 缺价原因聚合 + 零件号样本 |
| `mom_comparison` | 层2～4 | 上月同 scope 差分与**后端算好的比率** |
| `part_drilldown` | 层3或4 | 单零件 / 单 L0 头+摘要行 |

**禁止**默认打包：全量 items、合册 Excel、大图。

**dashboard 装包顺序（与分层叙事一致）：**  
`scope_meta` →（可选 gate 摘要）→ `month_overview` → `l0_top_drivers` → `l0_indirect_summary` → `missing_price_risk` → `mom_comparison`；需要材料故事时再加 `steel_price_summary` / `stamping_cost_summary`（或由对应提问单独装包）。

### 4.7 利用现有 Schema，禁止智能体「瞎想」（定稿）

**结论：可以，而且必须。** 分析侧不发明第二套业务字段；以现网 **Pydantic VO（及必要 DTO）为字段与序列化真相**，再投影成喂模型的 Pack + Schema 卡片。

#### 4.7.1 原则

| # | 原则 | 说明 |
|---|------|------|
| S1 | **键名同源** | Pack JSON 里出现的业务字段名 = 对应 VO 属性名（如 `grand_total`、`total_amount`、`stamping_amount`、`unit_cost`），禁止改成 `totalCost` / `月总成本` 等别名当主键 |
| S2 | **值域同源** | 金额用 VO 已约定的字符串小数位；`status` / `cost_source` / `audit_status` 等枚举只用库内真实取值，并在 Schema 卡片中列出允许值 |
| S3 | **释义受控** | 中文表头来自：`Field(description=…)` / 模型 docstring / **受控** `field_labels` 覆盖表（仅补 VO 缺 description 的字段）；禁止模型自由意译字段 |
| S4 | **只读投影** | Pack = VO 字段子集 + 后端算好的聚合字段（聚合字段也要有 Schema 条目，见 S6） |
| S5 | **缺字段不补脑** | JSON 无此键 → 报告不得写该指标；Prompt 写死「不得编造未出现字段」 |
| S6 | **聚合显式建模** | `*_sum` / `*_share` / 环比差额等若 VO 没有，须在 `llm` 切片定义 **TypedDict / 小型 Pydantic Pack 模型**，字段仍尽量引用 VO 原名作元素类型，并进入 Schema 卡片 |

#### 4.7.2 现网 Schema 索引（优先复用）

| 核算层 | 推荐锚定 VO / Schema | 路径（现网） |
|--------|----------------------|--------------|
| 层4 成品 L0 | `L0AssemblyCostVO`、`L0AssemblyCostItemVO`、`L0AssemblyCostIndirectVO` | `app/schemas/vo/l0_assembly_cost_vo.py` |
| 层3 冲压零件价 | `StampingPartCostVO` | `app/schemas/vo/stamping_part_cost_vo.py` |
| 层2 钢材联动 | `SteelPriceVO`（及 list summary VO） | `app/schemas/vo/steel_price_vo.py` |
| 层1 加工费 | `StampingProcessFeeVO` / Item VO | `app/schemas/vo/stamping_process_fee_vo.py` |
| 层1 L0 焊接费 | `BomL0WeldingFeeVO` 等 | `app/schemas/vo/bom_l0_welding_fee_vo.py` |
| 层0 引擎门禁 | `CostingEngine*` VO | `app/schemas/vo/costing_engine_vo.py` |
| 本切片输出 | `AnalysisReportVO` 等 | `app/schemas/vo/llm_analysis_vo.py`（拟新增，仍走 ApiResponse） |

`llm` 作为下游切片 **可以 import 上游 VO 类型**做投影与 `model_json_schema` 抽取；**禁止**改上游 VO 业务含义来迁就文案。

#### 4.7.3 运行时如何「把 Schema 给智能体」

```text
VO 类（现网）
  → SchemaCatalog.from_models([...], allowlist_fields)
       · model_json_schema() 或逐字段 title/description/type
       · 合并 field_labels 覆盖（中文采购用语）
       · 裁剪：只保留本 Pack allowlist（控 token）
  → schema_card（Markdown 或 JSON）注入 System Prompt
  → context_data（仅含 allowlist 键的数据）注入 User Prompt
```

注入片段示意（System Prompt 运行时追加）：

```text
【字段词典 — 只能使用下列字段，禁止发明新字段名】
L0AssemblyCostVO:
  grand_total = 总费用（月总账+间接），字符串金额
  total_amount = 月总账（不含间接）
  stamping_amount = 冲压小计（月链）
  purchased_amount = 年度价/外购小计（年侧）
  …
  status = 枚举：ok | partial | …（以词典列出的为准）

【数据解读铁律】
1. 数字必须来自本次 JSON；JSON 没有的字段一律不写。
2. 字段中文名必须用词典，不得自行翻译成易混淆叫法（尤其月总账 vs 总费用）。
3. 比率/占比只能使用 JSON 中已有的 *_share / *_rate / mom_* 字段。
```

参考项目同类做法：`FIELD_LABELS` + 运行时拼进 System Prompt；本产品升级为 **「VO Schema 自动抽取 + 受控中文覆盖」**，减少手工两套维护。

#### 4.7.4 Pack 与 VO 的绑定表（实现时维护一处）

| Pack ID | 主键名来源 VO | 允许的额外聚合键（须在 llm Pack Schema 声明） |
|---------|---------------|-----------------------------------------------|
| `month_overview` | `L0AssemblyCostVO` 金额字段名 | `l0_count`、`ok_count`、`partial_count`、`*_sum` |
| `l0_top_drivers` | 同上 + `part_number`/`part_name`/`status` | `mom_delta`、`mom_rate`（后端算） |
| `l0_indirect_summary` | `L0AssemblyCostIndirectVO` 的 `code`/`label`/`amount` | `indirect_amount_sum` |
| `stamping_cost_summary` | `StampingPartCostVO` | 分布计数、TopN 列表 |
| `steel_price_summary` | `SteelPriceVO` | 规格 TopN、加减价贡献汇总 |
| `part_drilldown` | L0 或冲压 VO 整行投影（allowlist） | 无则不加 |
| `engine_gate_digest` | `costing_engine_vo` 门禁项结构 | `navigate` 原样 |

#### 4.7.5 明确不做

- 不把整份 `model_json_schema()`（含所有嵌套、校验细节）无裁剪塞进 Prompt（浪费 token、干扰阅读）。  
- 不让 LLM 根据「字段名像什么」推断公式（公式只在核价服务；分析只读结果）。  
- 不在 `llm` 里复制一份与 VO 漂移的「文档型字段表」当长期真相——**真相在 VO；覆盖表只补中文**。

---

## 5. 目标架构

### 5.1 分层与依赖（对齐架构宪法）

**定稿：LLM 分析为独立垂直切片 `llm`，不挂在 `costing/` 下**，避免核价编排 / 公式代码与「报告生成 / Prompt / 模型客户端」搅在一起。

依赖方向（有向无环）：

```text
上游（被只读消费，不得反向依赖 llm）
  settings · stamping · bom · yishiyiyi · costing

下游（本切片）
  llm  → 只读组合 costing（及必要上游）结果；自管报告表与 LLM 调用
```

| 规则 | 说明 |
|------|------|
| `llm` → `costing`（等上游） | ✅ **只调用上游 Service** 稳定查询（paginate / get_by_id / get_ready 等）取 VO；**禁止**调用核价 Orchestrator 重算 |
| `llm` → 上游 Repository | ❌ **禁止**（C12：不另建取数通道，避免与 Service 规则/序列化分叉） |
| `costing` → `llm` | ❌ 禁止（引擎页仅可**打开助理浮动窗并预填 scope**，不 import llm Service） |
| `stamping`/`bom` → `llm` | ❌ 禁止 |

```text
┌─────────────────────────────────────────────────────────────┐
│  Frontend SPA：壳层浮动聊天助理（static/js/llm-assistant/）   │
│  顶栏帮助左侧机器人 → 浮动窗 / 最大化 / 右侧或底部小气泡       │
│  窗内选 scope → POST → 轮询 → Markdown（不占菜单、不进 features）│
└────────────────────────────┬────────────────────────────────┘
                             │ REST /api/llm/*
┌────────────────────────────▼────────────────────────────────┐
│  Router  app/routers/llm/{reports,tasks}.py                  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  app/services/llm/                                           │
│  analysis/report_service    幂等 / 任务 / 落库报告            │
│  context/aggregator         调上游 Service → 投影 Pack       │
│  catalog/                   只读 app/schemas VO → schema_card│
│  analysis/generator + prompts/registry + client/             │
│  AsyncTaskService（公共）                                    │
└───────┬───────────────────────────────┬─────────────────────┘
        │ 业务数据：仅 Service           │ 仅本切片报告表
        ▼                               ▼
  L0AssemblyCostService           LlmAnalysisReportRepository
  SteelPriceService               （读写 llm_analysis_reports）
  StampingPartCostService
  CostingEngineService …
  （返回 VO，再 allowlist 投影）
```

| 层 | 做 | 不做 |
|----|----|------|
| Router | DTO 入、VO 出、权限 | 查库、调 LLM、组 Pack |
| `analysis/` ReportService | 幂等、任务生命周期、事务落库报告 | 手写 SQL 查核价结果；改核价金额 |
| `context/` Aggregator | **调上游 Service** → 内存/VO 投影成 Pack | 直连 Repository；自写聚合 SQL |
| `catalog/` SchemaCatalog | 读 Schema 做词典 | 查业务库 |
| `analysis/` Generator + `client/` | Prompt + HTTP 调模型 | 查业务库 |
| Repository（llm） | **仅** `llm_analysis_reports` | 查询 steel_prices / stamping_part_costs / L0 等 |

**取数示例（定稿意图）：**

```text
dashboard Pack
  ← L0AssemblyCostService.paginate(db, year, month, location, …)
  ← 对返回的 list[L0AssemblyCostVO] 做 TopN / sum / ok|partial 计数（纯投影）
  ← 可选 SteelPriceService.paginate(… limit 摘要) 取行数或样本
  ← 可选 CostingEngineService.get_ready / list_runs 取完备性
禁止：
  ← llm/aggregate_repository.py 里 db.query(L0AssemblyCost)
  ← execute_sql / 另起「查核价工具」绕过 Service
```

若上游 Service **缺少**分析所需的稳定查询（例如「按 scope 汇总合计」），应 **在对应上游 Service 增补只读查询方法**（返回 VO / 命名汇总结构），再由 Aggregator 调用——**不在 llm 切片补 Repository。**

金额：`Decimal` → 与 VO serializer 一致的定长小数位字符串。

### 5.1.1 后端目录（独立切片 `llm`）

> **Service 层定稿分包**（`app/services/llm/`）：按能力分子包，**禁止在包根平铺新模块**；以后加功能只进对应子包。

```text
app/services/llm/
├── __init__.py                      # 包标记 + 子包职责索引（无业务实现）
├── catalog/                         # ★ Schema 字段真相（C9）— 已落地
│   ├── __init__.py
│   ├── schema_catalog.py            # VO → schema_card / Pack 预设 allowlist
│   └── field_labels.py              # 受控中文覆盖表
├── context/                         # Context Pack（C12：只调上游 Service）
│   ├── __init__.py
│   ├── aggregator.py                # LlmContextAggregator（待实现）
│   ├── pack_catalog.py              # report_type → pack_ids（待实现）
│   └── packs/                       # 单 Pack 投影器
│       ├── __init__.py
│       ├── scope_meta.py
│       ├── month_overview.py
│       ├── l0_top_drivers.py
│       ├── l0_indirect_summary.py
│       ├── stamping_cost_summary.py
│       ├── steel_price_summary.py
│       ├── missing_price_risk.py
│       ├── mom_comparison.py
│       ├── engine_gate_digest.py
│       └── part_drilldown.py
├── analysis/                        # 报告生命周期编排
│   ├── __init__.py
│   ├── report_service.py            # 幂等 / AsyncTask / 落库（待实现）
│   ├── generator.py                 # System+User → client（待实现）
│   └── idempotency.py               # （待实现）
├── prompts/                         # Prompt 静态资源 + 注册表 — md/yaml 已落地
│   ├── __init__.py
│   ├── registry.py                  # PromptRegistry（待实现）
│   ├── manifest.yaml
│   ├── _shared/
│   │   ├── currency_rules.md        # C10：禁止万元
│   │   └── anomaly_rules.md         # C11：异常分析
│   ├── system_buyer.md
│   ├── system_buyer_lead.md
│   ├── system_costing.md
│   ├── system_sales_quote.md
│   ├── system_exec.md
│   └── user_report_shell.md
├── client/                          # 模型 HTTP（与业务 Pack 隔离）
│   ├── __init__.py
│   └── openai_compatible.py         # （待实现）
└── export/                          # 报告导出 P2
    ├── __init__.py
    └── report_export_service.py
```

切片其余层（Router / Repository / Model / Schema）与 Service 并列、不塞进 `services/llm/`：

```text
app/
├── routers/llm/                     # reports.py / tasks.py
├── repositories/llm/                # 仅 report_repository（llm_analysis_reports）
│                                    # ❌ 不建 aggregate_repository
├── models/llm/                      # analysis_report.py
├── schemas/dto/llm_analysis_dto.py
├── schemas/vo/llm_analysis_vo.py
├── common/permissions/codes.py      # Perm.LLM_ANALYSIS_*（实现时）
└── main.py                          # include_router(llm)，勿挂到 costing 包
```

**分包规则（避免再拆一次）：**

| 要加的东西 | 放哪 |
|------------|------|
| 新字段标签 / Pack allowlist | `catalog/` |
| 新 Context Pack / 汇总口径 | `context/packs/` (+ 必要时 `pack_catalog`) |
| 报告任务 / 幂等 / 调模型编排 | `analysis/` |
| System/User Prompt 文案 | `prompts/`（静态）+ `prompts/registry.py` |
| 换模型厂商 / HTTP 重试 | `client/` |
| Markdown/文件下载 | `export/` |
| 另一产品能力（非核价报告） | **新建并列子包**（如 `llm/xxx/`），不塞进 `analysis/` 硬挤 |

**`context/packs/`：** 只做「Service VO → Context Pack 投影/汇总」，`from app.services.costing... import XxxService`，**不** `from app.repositories.costing...`。

`PromptRegistry` 加载 manifest 时须 **拼接 `_shared/*.md`**，计算 `prompt_hash`，写入 `llm_analysis_reports`。

### 5.1.2 前端目录（定稿：专用目录 `static/js/llm-assistant/`）

> **定稿（C13）：** 采购智能分析 = **壳层聊天助理**。  
> 全部前端代码落在 **`static/js/llm-assistant/`** 这一专用目录；**不**放进 `features/`（那是业务页），**不**注册 `pageMeta` / 侧栏菜单。

```text
static/
├── index.html                          # 仅：帮助左侧放机器人按钮挂载点（或由 boot 注入）
├── js/
│   ├── app.js                          # 登录成功后：import('./llm-assistant/boot.js')
│   ├── features/                       # 业务页（costing/bom/…）— 禁止塞助理实现
│   │   └── costing/engine/             # 仅可调用 window.LlmAssistant.open(...)
│   ├── llm-assistant/                  # ★ 前端专用目录（本切片唯一落点）
│   │   ├── boot.js                     # 入口：注入顶栏按钮、挂窗根、暴露 LlmAssistant + 就绪队列
│   │   ├── shell.js                    # 窗态机：closed | panel | maximized | docked
│   │   ├── template.js                 # 浮动窗 / 最大化 / docked 气泡 DOM
│   │   ├── api.js                      # 只封装 /api/llm/*
│   │   ├── chat/
│   │   │   ├── thread.js               # 消息列表
│   │   │   ├── composer.js             # 输入 + 发送
│   │   │   └── chips.js                # 常见提问胶囊
│   │   ├── scope/
│   │   │   └── bar.js                  # 窗内基地/年月/项目/BOM
│   │   ├── prompts/
│   │   │   └── catalog.js              # 对齐 §9.3
│   │   ├── storage/
│   │   │   └── conversation.js         # localStorage（C8）
│   │   ├── markdown/
│   │   │   └── render.js               # Markdown → HTML；必须 DOMPurify（§9.1.1）
│   │   └── task/
│   │       └── poller.js               # 轮询 AsyncTask
│   └── permissions.js                  # can('op:llm-analysis:…') 控制入口显隐
└── css/style.css                       # 不新增业务 class；助理用 Tailwind 任意值
```

**目录边界**

| 允许 | 禁止 |
|------|------|
| 助理相关 JS **只**写在 `static/js/llm-assistant/` | 在 `features/costing/**` 等业务页里复制助理 UI |
| 业务页只 `LlmAssistant.open / close` | 业务页直接 `fetch /api/llm` 绕过 `api.js` |
| `app.js` 一行 boot | 在 `features/index.js` 注册 `llm-analysis` 页面 |

**入口与窗态（定稿）**

| 元素 | 约定 |
|------|------|
| 入口图标 | 顶栏 `page-header-right`，**「使用帮助」左侧**；标准机器人线框；约 `w-8 h-8`；灰态，无脉冲 |
| 无权限 | 不渲染入口（`op:llm-analysis:view` / `run`） |
| `closed` | 仅入口图标 |
| `panel` | 浮动窗约 380×560；`z-index:110`；遮罩透明/轻模糊（§9.1.1） |
| `maximized` | 留边距大面板；可还原 |
| `docked` | ≥768px 屏幕**最右侧**小气泡；&lt;768px **底部悬浮**；点击回 `panel` |
| 切业务 Hash | 助理不卸载；scope 可预填，不强制弹窗 |

**明确禁止：** 侧栏菜单 / `#/llm-analysis` 占主区 / 开屏强弹 / 全屏压暗营销遮罩。

**与帮助：** `/helper/` 新开页；机器人是核价聊天助理，并列不替代。

**权限：** `op:llm-analysis:*`；不挂 `menu:llm-analysis` 到侧栏。

**业务唤起：** `window.LlmAssistant.open({ scope, promptId?, part_number? })`（就绪队列见 §9.1.1）。

### 5.1.3 前后端协作时序（文件级）

```text
static/js/llm-assistant/boot.js（壳层常驻）
  → 用户点机器人 / LlmAssistant.open(...)
  → chat/composer 或 chips
  → api.js.createReport(dto)
      → POST /api/llm/reports
          → routers/llm/reports.py
          → services/llm/analysis/report_service.py
              → analysis/idempotency + repositories/llm/report_repository
              → AsyncTaskService.create + submit(worker)
  → task-poller.js.poll(task_id)
      → GET /api/llm/tasks/{id}
  → api.js.getReport(report_id)
      → markdown-view 写入助手气泡；conversation-store 持久化

后台 worker（analysis/report_service）：
  context/aggregator.build(report_type, scope)
    → context/packs/*.py
    → 上游 Service.paginate / get_by_id / get_ready …（返回 VO）
    → allowlist 投影 + 内存汇总（*_sum / TopN）
    → catalog/ SchemaCatalog 只读 schemas（非业务库）
  prompts/registry.resolve(audience)
  analysis/generator.generate(packs, schema_card, prompt) → client/
  report_repository.update(succeeded | failed)   # 仅报告表
  async_task 写入 result_json.report_id
```

### 5.1.4 配置与密钥

| 项 | 建议位置 | 说明 |
|----|----------|------|
| LLM `base_url` / `api_key` / `model` | 环境变量或独立 settings 段（如 `LLM_*`） | **仅** `app/services/llm/client/` 读取；禁止进 `costing` 配置文件 |
| 任务超时、幂等 TTL | `llm` 切片常量 / settings | 默认 120s / 5min |
| 租户显示名、水印文案 | 可配置 | 满足商号中立 C7 |

### 5.2 数据流（REST + 异步任务，生产主路径）

```text
前端：在浮动助理内选好 scope → 点胶囊或发送问题
        │
        ▼
POST /api/llm/reports
  body: { report_type | auto, scope, user_question, idempotency_key?, … }
        │
        ├─ 幂等命中（§10.2）→ 直接返回已有 report / task（succeeded）
        │
        ▼
创建 AsyncTask + llm_analysis_reports 行（status=pending/running）
返回 202 语义（HTTP 可用 200 + ApiResponse，与现网任务创建一致）：
  { task_id, report_id, status: "processing" }
        │
        ▼
后台：Aggregator 装 Pack → PromptRegistry 取版本化 Prompt
      → LLM 一次完整生成 → 写 markdown_content / token / 状态
        │
        ▼
前端轮询 GET /api/llm/tasks/{task_id}
  （或复用现网 /api/async-tasks/{id}，见 §5.3）
  status=succeeded → GET /api/llm/reports/{report_id}
  渲染 markdown_content；失败展示 error_message
```

**超时策略（定稿：方案 B）**

| 项 | 约定 |
|----|------|
| 主路径 | **异步任务 + 轮询**；网关保持常规超时即可 |
| 预估耗时 | 聚合 1～5s + LLM 5～30s（高峰可能更长） |
| 任务超时 | 建议硬上限 **120s**（可配置）；超时 → `failed`，可重试 |
| 方案 A（长同步） | **不作为主路径**；仅本地调试脚本允许 |

### 5.3 REST 端点（胶囊快捷 + 自由输入同路径）

> **同一入口**：胶囊与自由输入都走 `POST /api/llm/reports`。  
> P0 **不做**第二套 Chat/Tool Calling；意图解析用 **轻量规则**（§5.3.1），失败则 **默认 `dashboard`**，仍生成报告并优先回答 `user_question`。

| Method | Path | 用途 |
|--------|------|------|
| `POST` | `/api/llm/reports` | 提交生成（胶囊或自由输入） |
| `GET` | `/api/llm/tasks/{task_id}` | 任务状态（若与全局 AsyncTask 合并则可省略本路径） |
| `GET` | `/api/llm/reports/{report_id}` | 取完整报告 VO |
| `GET` | `/api/llm/reports` | 按 scope 列表历史报告（分页） |
| `POST` | `/api/llm/reports/{report_id}/export` | 可选：导出 md/docx（P2） |

`report_type` → Packs（固定映射，后端写死；受众见 §1A.7）：

| `report_type` | 产品按钮文案（采购口吻） | 加载 Packs |
|---------------|--------------------------|------------|
| `dashboard` | 本月采购成本总览 | `scope_meta` + `month_overview` + `l0_top_drivers` + `l0_indirect_summary` + `missing_price_risk` +（有上月则）`mom_comparison` |
| `steel` | 钢材联动议价参考 | `scope_meta` + `steel_price_summary` + `mom_comparison` |
| `stamping_part` | 冲压件采购价分析 | `scope_meta` + `stamping_cost_summary` + `missing_price_risk` |
| `l0` | 供货总成（对主机厂）成本 | `scope_meta` + `l0_top_drivers` + `l0_indirect_summary` +（可选）`mom_comparison` |
| `part_drilldown` | 单号议价卡 | `scope_meta` + `part_drilldown`（必传 `part_number`） |
| `gate` | 主数据 / 缺价阻塞清单 | `scope_meta` + `engine_gate_digest` |
| `exec_brief` | 管理层一页纸（P1+） | 精简版 `month_overview` + Top5 + 风险计数 |
| `auto` | （仅请求入参）自由输入未指定类型 | **不进 Pack 表**；由 §5.3.1 解析成上表之一后再装包 |

请求体示意（**胶囊**）：

```json
{
  "report_type": "dashboard",
  "audience": "buyer_lead",
  "user_question": "青岛 2025年1月的采购成本总体怎么样？",
  "prompt_id": "Q01",
  "scope": {
    "location": "青岛",
    "year": 2025,
    "month": 1,
    "vehicle_model": "T28",
    "bom_version": "V1"
  },
  "engine_run_id": 123,
  "idempotency_key": "dashboard|buyer_lead|青岛|2025|1|T28|V1|q:sha256:…|user:42",
  "force_refresh": false
}
```

请求体示意（**自由输入，不点胶囊**）：

```json
{
  "report_type": "auto",
  "user_question": "2025年01月的情况怎么样，钱主要花哪了？",
  "scope": {
    "location": "青岛",
    "year": 2025,
    "month": 1,
    "vehicle_model": "T28",
    "bom_version": "V1"
  },
  "idempotency_key": "auto|青岛|2025|1|T28|V1|q:sha256:…|user:42",
  "force_refresh": false
}
```

| 字段 | 约定 |
|------|------|
| `user_question` | **必填**（胶囊用展示文案；自由输入用原文）。注入 User Prompt，模型须**优先回答该问**，且只能用 Pack 内数据 |
| `report_type` | 胶囊：枚举值；自由输入：可传具体类型，或传 **`auto`** 交给后端解析 |
| `prompt_id` | 可选；胶囊传 `Q01` 等；自由输入可空 |
| `audience` | 可选；缺省按解析后的 `report_type`（§1A） |
| 幂等 key | **必须含 `user_question` 指纹**（如归一化后 sha256 前 16 位），避免同 scope 不同问题误复用报告 |

落库时额外记：`resolved_report_type`（`auto` 解析结果）、`user_question`、`intent_source`（`chip` / `rule` / `default_dashboard`）。

`audience` 可选；缺省按 §1A.1。权限：`Depends(require_perm(Perm.LLM_ANALYSIS_RUN))` 等（实现时落 `permission-design.md`）。

#### 5.3.1 自由输入意图解析（P0 定稿：规则优先，默认 dashboard）

**目标：** 不点胶囊也发请求；**不**为意图再调一次 LLM（避免双倍延迟与费用）。

```text
前置（前端）：
  scope 不齐 → 仅本地提示「请先选定基地 / 年月 / 项目」，不发请求
  user_question 空白 → 不发请求
  否则 → 一律 POST（report_type 可用 auto）

后端 IntentResolver（纯规则，放 analysis/ 或 context/pack_catalog 旁）：
  1. 从原文抽取疑似 part_number → resolved = part_drilldown（写入 scope.part_number）
  2. 否则关键词表（可与 §9.3 对齐）：
       缺价|partial|算不全 → dashboard（或 stamping_part，见配置）
       跑不起来|门禁|主数据 → gate
       钢材|吨价|厚宽|加减价 → steel
       冲压件|加工费|材料净 → stamping_part
       总成|间接|对主机厂 → l0
       一页纸|汇报|领导 → exec_brief
  3. 否则 → resolved = dashboard（默认兜底）
  4. 按 resolved 装 Pack → 生成（User Prompt 含原文 user_question）
```

| 原则 | 说明 |
|------|------|
| 默认宽装包 | 猜不准时用 `dashboard`（月度全景 Pack），让模型在数据内回答「情况怎么样」 |
| 答不上来也要出报告 | 问题与核价无关时，报告开头说明「当前数据无法回答该问」，并仍给出本月 KPI / 异常专节（C11）——**禁止**静默空回复 |
| 前端可选预解析 | 可做同样关键词高亮/预选胶囊，但**不得**因未匹配而拦截 POST |
| P1+ 可选 | 规则置信度低时用小模型分类；仍禁止 Tool Calling 开放域 |

### 5.4 与核价引擎衔接

| 时机 | 行为 |
|------|------|
| 引擎 `succeeded` | 可选自动 `POST` 一份 `dashboard`（同 AsyncTask 通道） |
| 引擎硬停 | 仅允许 `gate`；其它 `report_type` 返回业务错误「尚无完整核价结果」 |
| 未审核结果 | `metadata.audit_hint` 标注草稿；Prompt 同步约束措辞 |

报告**不替代**月度合册 Excel。

### 5.5 MCP（非 P0）

MCP 仅作外部 Agent 可选接入；产品内嵌 UX = 对话壳。  
若暴露 Tools，**工具实现仍须走同一套上游 Service**，禁止 MCP 直连 SQL / 另起取数工具（C12）。

---

## 6. 报告响应契约（输出侧，前端 VO）

> 与 §8 Context Pack（**喂 LLM 的输入**）分离。本节是 **REST 返回给前端的契约**。

统一外层：`ApiResponse[T]`（见 `docs/api-type-safety.md`）。  
创建任务成功时 `data` 为任务摘要；拉报告时 `data` 为 `AnalysisReportVO`。

### 6.1 创建任务响应 `AnalysisReportTaskVO`

```json
{
  "task_id": "a1b2c3d4",
  "report_id": 1001,
  "status": "processing",
  "report_type": "dashboard",
  "scope": {
    "location": "青岛",
    "year": 2025,
    "month": 1,
    "vehicle_model": "T28",
    "bom_version": "V1"
  },
  "from_cache": false,
  "progress_percent": 0,
  "message": "正在聚合核价结果…"
}
```

`status`：`pending` | `processing` | `succeeded` | `failed`（与现网 AsyncTask 对齐用词以落地时统一为准）。

### 6.2 完整报告 `AnalysisReportVO`

```json
{
  "report_id": 1001,
  "task_id": "a1b2c3d4",
  "report_type": "dashboard",
  "audience": "buyer_lead",
  "scope": {
    "location": "青岛",
    "year": 2025,
    "month": 1,
    "vehicle_model": "T28",
    "bom_version": "V1",
    "stamping_supplier": null
  },
  "status": "succeeded",
  "markdown_content": "# 2025年1月青岛基地 T28 核价分析报告\n\n…",
  "error_message": null,
  "metadata": {
    "engine_run_id": 123,
    "has_data": true,
    "data_message": "已加载 L0=27，全部 ok",
    "generated_at": "2026-08-22T10:00:00+08:00",
    "llm_model": "qwen-max",
    "prompt_version": "v1.2.3",
    "prompt_hash": "sha256:abcdef…",
    "context_pack_ids": [
      "scope_meta",
      "month_overview",
      "l0_top_drivers",
      "l0_indirect_summary",
      "missing_price_risk",
      "mom_comparison"
    ],
    "prompt_tokens": 4200,
    "completion_tokens": 1800,
    "total_tokens": 6000,
    "from_cache": false,
    "audit_hint": null
  },
  "attachments": {
    "top_l0_by_grand_total": [
      {
        "part_number": "502005511AA",
        "part_name": "左侧围内板后部上段总成（五座）",
        "grand_total": "226.5333",
        "status": "ok"
      }
    ],
    "month_overview_kpis": {
      "l0_count": 27,
      "grand_total_sum": "1424.5716",
      "total_amount_sum": "1265.3048",
      "indirect_amount_sum": "159.2668"
    }
  }
}
```

| 字段 | 说明 |
|------|------|
| `markdown_content` | 完整报告正文；前端 Markdown 渲染 |
| `attachments` | **可选**：从 Context Pack 抽出的图表/表格数据，便于 UI 画图且与正文数字同源；不得与 Pack 矛盾 |
| `metadata.prompt_version` / `prompt_hash` | 见 §10.3；页脚展示「报告生成版本：v1.2.3」 |
| 金额 | 字符串，禁止 JSON number float |

失败时 `status=failed`，`markdown_content` 可空，`error_message` 给人看。

---

## 7. Prompt 与业务口径

### 7.1 智能体人设（按 audience 切换侧重点）

**默认（采购）：**

> 你是冲焊装配企业**采购部的成本分析助手**。本公司向主机厂客户交付冲焊供货总成，并向各类配件 / 冲压等供应商采购。  
> 你的读者是采购员或采购主管：帮他们看清「本月该付多少、哪里在涨、缺什么价、下一步催谁」。  
> 只基于系统提供的结构化 JSON 解读，**不重新计算**单价与总费用，**不代替采购员做议价承诺**。

| `audience` | 语气与侧重 |
|------------|------------|
| `buyer` | 短句、零件号清单、催办/约谈动作优先；少战略空话 |
| `buyer_lead` | 先总盘与结构，再风险与分工线索，最后附件式 Top 表 |
| `costing` | 口径严谨、缺口与 navigate、审核状态 |
| `sales_quote` | 成品总费用与构成；避免供应商议价细节外泄口吻 |
| `exec` | 结论 ≤ 5 条；禁止大表 |

### 7.2 口径硬约束（摘录）

1. `total_amount`（月总账）不含间接；`grand_total`（总费用）= 月总账 + 间接——对采购口述时可称「未含间接的材料与加工合计」vs「含间接的成品成本」。  
2. 禁止混用上述两个概念。  
3. `partial` / 缺价必须单独成段，不得并入「一切正常」的汇总。  
4. 比率只用 JSON 已算字段。  
5. 归因无证据时写「需下钻核实」；禁止捏造钢厂报价或供应商口头承诺。  
6. 标题写具体「基地 + 年-月 + 项目」，禁止「本月」。  
7. **字段**：只能使用本次注入的 **Schema 词典**（§4.7）中的键名与中文名；禁止发明字段或改口径。  
8. **金额单位（C10，冒烟已踩坑）**：  
   - JSON 中金额为 **元**（勿写「万元」）。  
   - **严禁**把 `1381.9896` 写成「1381.99 万元」或「约 0.14 亿元」。  
   - **严禁**对金额做 ÷10000 / ×10000 换单位。  
   - 表述须带单位「元」或「元/件」；`meta.currencyNote` 有则原样遵守。  
9. **异常分析（C11）**：见 §7.5；有风险字段必须出板块，无则明示「未见」。  
10. 涉及下游时用「客户 / 主机厂」表述，**不生成对客正式函**；禁止在默认 Prompt 中写死具体主机厂或本公司商号。  
11. 建议动作须可执行（见 §1A.8）。

### 7.3 `dashboard` 板块顺序（采购总览 · 对齐 §4 分层）

1. **结论摘要**（总费用、环比、缺价件数；金额带「元」）  
2. 范围与本月是否跑通（层0/引擎）  
3. **成本结构**：五块积木（标清年侧/月侧）+ 间接  
4. **月动因**：①冲压及钢材线索（若 Pack 已带）  
5. 头部成品 / 涨幅 Top  
6. **异常与风险**（§7.5，强制）  
7. **下周行动清单**  

### 7.3.1 分层归因（必须写入 System Prompt）

见 §4.4.2 口诀：总费用变动先查月链①与间接，再查年侧②③④异常；禁止把年焊接费说成「本月钢价导致」。

### 7.4 生成参数

- `temperature ≤ 0.2`；`max_tokens` 建议 2k～4k  
- 超长可拆两次任务（总览 / 附录），P0 先单次完整报告  

### 7.5 异常分析（定稿）

报告须能识别并分节叙述下列异常（仅基于 Pack，不臆造）：

| 类型 | 数据线索 | 报告要求 |
|------|----------|----------|
| 核算不全 | `calc_status=partial` / `partial_count>0` / `missing_leaf_count` | 列出零件号样本 + 建议催价/补主数据 |
| 缺价风险 | `missingPriceRisk` | 原因计数 + 样本；禁止说「全部正常」 |
| 门禁硬停 | `engine_gate_digest` / gate | 缺什么、navigate 去哪上传 |
| 月环比异常 | `mom_comparison` 中后端标出的高涨跌 | 点名分项（①月链 vs 年侧） |
| 头部集中 | TopN 占比（若 Pack 已给或可从 Top 表只做**加总展示**且不加未经后端的占比字段则只列绝对额） | 提示议价优先级；占比优先用后端字段 |
| 数据空窗 | `hasData=false` | 友好说明无核算结果，勿编造金额 |

**无异常时**：专节写「本次 Pack 显示 partial_count=0 / 缺价样本为空，未见核算不全或缺价风险。」

Prompt 落盘路径（只维护文件、由日后 PromptRegistry 加载）：`app/services/llm/prompts/`（见 §5.1.1）。

---

## 8. Context Pack JSON 契约（输入侧示意）

```json
{
  "meta": {
    "scope": {
      "location": "青岛",
      "year": 2025,
      "month": 1,
      "vehicle_model": "T28",
      "bom_version": "V1",
      "stamping_supplier": null
    },
    "report_type": "dashboard",
    "hasData": true,
    "dataMessage": "已加载 L0=27，全部 ok",
    "generatedAt": "2026-08-22T00:00:00+08:00",
    "currencyNote": "金额单位：元/件（单车用量已计入）"
  },
  "monthOverview": {
    "l0_count": 27,
    "ok_count": 27,
    "partial_count": 0,
    "total_amount_sum": "1265.3048",
    "grand_total_sum": "1424.5716",
    "breakdown": {
      "stamping_amount": "736.6998",
      "purchased_amount": "344.0410",
      "bundle_amount": "13.7600",
      "welding_amount": "170.8040",
      "welding_other_amount": "0.0000"
    },
    "indirect_amount_sum": "159.2668"
  },
  "l0TopDrivers": {
    "by_grand_total": [
      {
        "part_number": "502005511AA",
        "part_name": "左侧围内板后部上段总成（五座）",
        "grand_total": "226.5333",
        "total_amount": "197.5929",
        "status": "ok"
      }
    ]
  },
  "missingPriceRisk": {
    "partial_count": 0,
    "missing_part_numbers_sample": [],
    "reason_counts": {}
  },
  "momComparison": null
}
```

字段中文名表运行时注入 System Prompt（对齐参考项目 `FIELD_LABELS`）。

---

## 9. 产品形态（前端）：壳层聊天助理

> **不是业务页。** 用户在任意核价/列表页工作；助理是顶栏旁的轻量工具（C13）。

### 9.1 入口与三种窗态

```text
顶栏右侧：  [业务动作…]  [机器人图标]  [使用帮助]  [头像]
                              │
              ┌───────────────┼───────────────────────┐
              ▼               ▼                       ▼
           panel           maximized                docked
         浮动聊天窗         近全屏浮层         右侧气泡 / 窄屏底部
```

| 态 | 用户操作 | 视觉要求（不抢镜头） |
|----|----------|----------------------|
| 入口 | 未打开时仅图标 | 与帮助钮同规格；灰字；无 badge 轰炸、无自动弹出 |
| `panel` | 点机器人 | 浮动聊天窗；直角暗色；**无压暗业务底**（见 §9.1.1）；`z-index: 110` |
| `maximized` | 窗内「最大化」 | 留边距大面板；可还原到 `panel`；遮罩透明/轻模糊 |
| `docked` | 窗内「最小化」 | ≥768px 贴**最右侧**；&lt;768px **底部悬浮**（§9.1.1）；一键回 `panel` |

关闭：窗内 × → `closed`（只留顶栏图标）。最小化 ≠ 关闭。

#### 9.1.1 壳层工程约束（定稿补强）

| 项 | 定稿 | 对错判定 / 说明 |
|----|------|----------------|
| **z-index** | 助理浮层（`panel` / `maximized` / `docked` 气泡）**统一 `z-index: 110`** | 现网阶梯：页眉 70 → 抽屉 80/85 → 侧栏遮罩/侧栏 90/100 → **助理 110** → Toast 9999。助理高于侧栏，便于点开后操作；**低于 Toast**，错误提示不被挡住。**禁止**用 10000 这类天文数字。 |
| **遮罩** | 若 `maximized`/`panel` 需要点击外侧关闭：遮罩 **`z-index: 109`**（略低于面板），背景须 **透明或极轻微 `backdrop-blur`**，**禁止**半透明黑/灰全屏盖住业务页底色 | ✅ 对齐 C13「不抢镜头」。遮罩只点透关闭，不做压暗 Modal。 |
| **`LlmAssistant` 就绪队列** | `window.LlmAssistant` 须在 `boot.js` 最早注入 **stub**：`open/close/...` 把调用推入队列；`shell` 就绪后 flush。业务页任意时刻 `LlmAssistant.open(...)` **不得因 undefined 抛错** | ✅ 正确且必做：引擎/列表可能早于助理模块执行。 |
| **Markdown 净化** | 助手气泡渲染 **必须**先经 **DOMPurify**（或同等白名单净化）再写入 DOM；CSP 可并行启用，但是**第二道**，不能替代净化 | ✅ 正确：模型 Markdown 视为不可信 HTML。实现时引入依赖并单测脚本注入。 |
| **`docked` 响应式** | 视口宽度 **≥ 768px**：贴**屏幕最右侧**小气泡（桌面定稿）。**&lt; 768px**：降级为**底部居中/偏右悬浮气泡**，避免挡住纵向滚动条与拇指热区 | ✅ 正确；原先文档未写，现升为设计要求，开发不得只做桌面右侧。 |

```text
// 就绪队列示意（设计约束，非最终实现）
window.LlmAssistant = window.LlmAssistant || {
  _q: [],
  open(...args) { this._q.push(["open", args]); },
  close(...args) { this._q.push(["close", args]); },
};
// boot 完成后：用真实现替换，并 flush _q
```

### 9.2 浮动窗内部布局

窗内仍是对话，不是多按钮报告中心：

| 区域 | 内容 |
|------|------|
| 标题栏 | 「采购助理」短名 + 最大化 / 最小化 / 关闭；无「AI / LLM」营销字样 |
| scope 条 | 基地 / 年 / 月 / 项目 / BOM（必选后才能提问）；可从当前业务页或 `LlmAssistant.open` 预填 |
| 主区线程 | 用户气泡 + 助手气泡（Markdown **须 DOMPurify 后再渲染**，§9.1.1）；进行中「分析中…」 |
| 底部 | 常见提问胶囊（§9.3）+ 输入框 + 发送；「清空本机对话」 |
| 页脚小字 | `prompt_version`（有回复时） |

从零件价 / L0 列表「解读此条」：`LlmAssistant.open({ scope, part_number })` → 打开 `panel` → 自动塞入 Q51 并发送。

文案避免对业务用户暴露「LLM / Token / Context Pack」；**无流式打字机效果**。

### 9.3 常见提问目录（设计定稿）

前端 `suggested-prompts.js` 维护；点击即填入用户气泡并带上映射字段。占位符 `{location}` `{year}` `{month}` `{vehicle_model}` `{part_number}` 由当前 scope 替换。

#### A. 采购总览 / 主管

| ID | 用户可见提问 | `report_type` | `audience` |
|----|--------------|---------------|------------|
| Q01 | `{location} {year}年{month}月的采购成本总体怎么样？` | `dashboard` | `buyer_lead` |
| Q02 | 这个月钱主要花在哪一块（冲压 / 外购 / 焊接 / 间接）？ | `dashboard` | `buyer_lead` |
| Q03 | 哪些供货总成最贵？优先跟哪些件议价？ | `l0` | `buyer` |
| Q04 | 和上个月比，成本涨了还是降了？涨在哪里？ | `dashboard` | `buyer_lead` |
| Q05 | 给我一页纸，方便跟领导汇报。 | `exec_brief` | `exec` |

#### B. 缺价 / 阻塞 / 年侧齐套

| ID | 用户可见提问 | `report_type` | `audience` |
|----|--------------|---------------|------------|
| Q11 | 还有哪些零件缺价或算不全（partial）？ | `dashboard` | `buyer` |
| Q12 | 为什么这个月核价跑不起来？主数据还缺什么？ | `gate` | `buyer_lead` |
| Q13 | 缺价清单按工厂拆一下，我好分头催。 | `stamping_part` | `buyer` |
| Q14 | 今年的加工费、焊接费算齐了吗？不齐会影响什么？ | `dashboard`（P1 带 `annual_calc_digest`） | `buyer_lead` |

#### C. 钢材 / 材料采购

| ID | 用户可见提问 | `report_type` | `audience` |
|----|--------------|---------------|------------|
| Q21 | 本月钢材联动价哪些规格在涨？ | `steel` | `buyer` |
| Q22 | 厚宽加减价对单价影响大吗？举几个规格。 | `steel` | `buyer` |
| Q23 | 钢材侧环比变动最大的 Top 规格是哪些？ | `steel` | `buyer` |

#### D. 冲压件采购

| ID | 用户可见提问 | `report_type` | `audience` |
|----|--------------|---------------|------------|
| Q31 | 哪些冲压件材料净成本异常偏高？ | `stamping_part` | `buyer` |
| Q32 | 按冲压工厂看，哪边更贵或更缺价？ | `stamping_part` | `buyer` |
| Q33 | 加工费和材料费大概各占多少？ | `stamping_part` | `buyer` |

#### E. 成品（对主机厂交付）

| ID | 用户可见提问 | `report_type` | `audience` |
|----|--------------|---------------|------------|
| Q41 | 交给主机厂的总成里，总费用 Top 有哪些？ | `l0` | `sales_quote` |
| Q42 | 间接费用（运输、管理等）合计多少？结构怎样？ | `l0` | `buyer_lead` |
| Q43 | 哪些总成是 partial，对外沟通要小心？ | `l0` | `sales_quote` |

#### F. 单号议价

| ID | 用户可见提问 | `report_type` | 备注 |
|----|--------------|---------------|------|
| Q51 | 帮我解读零件号 `{part_number}`，我怎么跟供应商谈？ | `part_drilldown` | 无零件号则先弹输入 |
| Q52 | `{part_number}` 贵在材料、加工还是别的？ | `part_drilldown` | 同上 |

#### G. 输入框（非胶囊）— 定稿：也发请求

| 条件 | 行为 |
|------|------|
| scope **不齐** | **唯一**可不发请求：本地提示补全基地 / 年月 / 项目 |
| `user_question` 空白 | 不发请求 |
| scope 齐 + 有问题 | **一律 POST**；`report_type` 建议 `auto`（或前端轻规则预填具体类型） |
| 关键词命中 §9.3 | 后端（或前端预填）解析到对应 `report_type`，**仍走同一生成链路** |
| 含疑似零件号 | 解析为 `part_drilldown` |
| 无法匹配关键词 | **`dashboard` 兜底**装包；Prompt 带原文；模型优先答该问 |

胶囊 = 快捷填 `report_type` / `audience` / `prompt_id` + 标准问句；**与自由输入共用 API**，不是两套产品。

P0 至少上线：**Q01、Q03、Q11、Q12、Q21、Q31、Q41、Q51** + **自由输入 → auto/dashboard**；其余提问胶囊 P1 补齐。

### 9.4 对话历史：localStorage（定稿）

| 项 | 约定 |
|----|------|
| 存储位置 | **仅浏览器 `localStorage`**；不写服务端会话表 |
| Key 建议 | `llm_chat_v1:{userId}:{scopeKey}`；`scopeKey` = 规范化 `location\|year\|month\|vehicle_model\|bom_version` |
| 换 scope | 切换顶栏 scope → 加载该 key 下线程；互不混聊 |
| 与服务端报告 | 气泡可挂 `report_id`；需要时可再 `GET /api/llm/reports/{id}` 刷新正文；**聊天顺序与文案以 localStorage 为准** |
| 清空 | 「清空本机对话」只删当前 key；不删服务端 `llm_analysis_reports` |
| 容量 | 单 key 建议上限约 **50 条消息**或 **~1.5MB**；超出淘汰最旧轮次；超大 Markdown 可只存 `report_id` + 摘要，打开时再拉全文 |
| 安全 | 勿存 token；`userId` 与登录会话一致；退出登录可选择清空全部 `llm_chat_v1:*`（产品可选） |
| 局限 | 换浏览器 / 清缓存 / 隐私模式 → 历史消失；需跨设备时走 P2+ 服务端会话（非本期） |

**消息结构示意（存 localStorage）：**

```json
{
  "version": 1,
  "conversation_id": "c_local_xxx",
  "scope": {
    "location": "青岛",
    "year": 2025,
    "month": 1,
    "vehicle_model": "T28",
    "bom_version": "V1"
  },
  "updated_at": "2026-08-22T10:00:00+08:00",
  "messages": [
    {
      "id": "m1",
      "role": "user",
      "prompt_id": "Q01",
      "content": "青岛 2025年1月的采购成本总体怎么样？",
      "created_at": "…"
    },
    {
      "id": "m2",
      "role": "assistant",
      "status": "succeeded",
      "report_id": 1001,
      "task_id": "a1b2c3d4",
      "report_type": "dashboard",
      "content_markdown": "# …",
      "prompt_version": "v1.2.3",
      "created_at": "…"
    }
  ]
}
```

进行中消息：`status: "processing"` + `task_id`；刷新页面后 `task-poller` 根据未完成 `task_id` 续询，完成再写回 localStorage。

### 9.5 其它入口（唤起助理，不跳菜单页）

| 入口 | 行为 |
|------|------|
| 顶栏机器人 | 打开 / 关闭 `panel`（主入口） |
| 核价引擎成功 | `LlmAssistant.open({ scope, promptId: 'Q01' })`（可选，勿强制弹） |
| 列表「解读此条」 | `open({ scope, part_number })` 并触发 Q51 |
| 服务端报告审计（可选 P2） | **独立设置/审计页**，与聊天助理壳分离；**不替代** localStorage 对话流 |

### 9.6 权限

- 入口与发送：`op:llm-analysis:view` / `op:llm-analysis:run`（无权限不显示机器人图标）  
- **不**把 `menu:llm-analysis` 挂到侧栏  
- `sales_quote` 可见成品类提问；含供应商议价细节的完整回复按权限码控制  

---

## 10. 安全、幂等、版本与质量门禁

### 10.1 基础

1. 分析链路对核价结果表**只读**。  
2. 鉴权 + 基地数据范围与列表 API 一致；**对客敏感**：默认报告仅本公司（租户）内部角色；导出外传需人工确认（产品提示，非自动发主机厂）。  
3. 审计：`user_id、scope、report_type、resolved_report_type、user_question、audience、pack_ids、model、prompt_version、prompt_hash、task_id、tokens`。  
4. 降级：LLM 不可用时可返回「规则模板报告」（仅拼装 KPI Markdown，`metadata.llm_model=null`）——采购仍能拿到总盘数字。

### 10.2 幂等与防重复点击（定稿）

| 规则 | 说明 |
|------|------|
| 客户端 key | `report_type` + 规范化 scope + **`user_question` 指纹** + `user_id`（+ audience）；同问连点合并；**换问题必须换 key** |
| 缓存命中 | 同用户 + 同 key + `force_refresh=false`：TTL 内（默认 5min）已有 `succeeded` → 直接返回，`from_cache=true`，不调 LLM |
| 进行中去重 | 同 key 已有 `pending/processing` → 返回该 `task_id`，不开第二路 LLM |
| `force_refresh` | `true` 跳过成功缓存，新开任务（进行中去重仍可保留） |

规范化 scope：字段 trim、车型/版本大小写规则与现网列表查询一致。命中条件须含问题指纹，避免「同月不同问」误复用。

### 10.3 Prompt / 报告版本强关联（定稿）

表 `llm_analysis_reports`（名以落地为准）至少包含：

| 列 | 用途 |
|----|------|
| `prompt_version` | 语义版本，如 `v1.2.3`，产品可见 |
| `prompt_hash` | System+User 模板 + **schema_card 摘要** 内容哈希，防漏改版本号 |
| `engine_run_id` | 可选，绑定当时核价 Run |
| `context_pack_snapshot` | 可选 JSON/压缩；争议时复盘「喂了什么数」 |
| `markdown_content` | 完整正文 |
| `llm_model` / token 字段 | 成本与追溯 |

前端报告底部固定小字：`报告生成版本：{prompt_version} · 模型：{llm_model} · 生成于 {generated_at}`。  
改 Prompt 措辞必须 bump `prompt_version`；业务质疑「为何语气变了」可对版本解释。

### 10.4 验收

固定 scope（如青岛 T28 2025-01）黄金 Pack + 检查清单：口径、禁编造、页脚版本、幂等第二次不增 token、**报告未出现 Schema 词典外字段名**。

---

## 11. 分期落地

| 阶段 | 交付 | 不做 |
|------|------|------|
| **P0** | **壳层浮动助理**（帮助左侧机器人；panel/最大化/右侧气泡）+ localStorage；胶囊 + 自由输入均 POST；`auto`/dashboard；异步生成；幂等 | 流式、侧栏菜单页、开屏强弹、无 scope 闲聊、Tool Calling、服务端会话表、MCP |
| **P1** | 补齐 §9.3 全部提问；`exec_brief`；`audience`；环比强化；attachments；续询未完成 task | 改核价公式、自动议价目标 |
| **P2** | 导出 Word/PDF；可选 MCP；可选服务端报告审计列表（仍非聊天主存） | 合册当 LLM 主输入 |
| **P3** | 多月趋势、跨基地；可选「云端同步对话」（若产品需要，另立需求） | 自动改主数据 / 自动重跑引擎 |

---

## 12. 明确非目标

- LLM 替代核价 Orchestrator  
- SSE/WebSocket 流式报告  
- 无 scope 闲聊 / Tool Calling 开放域 / **服务端多轮对话 Session**（历史用 localStorage）  
- 向量库 RAG（首期）  
- 长同步 REST 作为生产主路径  
- 不让 LLM 根据「字段名像什么」推断公式或中文口径（**以 Schema 词典为准**，§4.7）  
- **在 `llm` 切片另建核价结果取数 Repository / 独立 SQL 工具**（C12：数据只经上游 Service）  
- **把 LLM / Prompt / 模型客户端塞进 `app/services/costing/`**（污染核价切片）  
- **侧栏菜单页 / `#/llm-analysis` 占满主区抢业务视线**（C13：壳层浮动助理）  
- **自动向主机厂发报价 / 自动向供应商下发议价函**  
- **替采购员决定目标价或合同条款**  
- 供应商或主机厂账号直接使用本智能体（除非另立项目与权限模型）  

---

## 13. 决策摘要（评审用）

| 议题 | 决策 |
|------|------|
| 业务主体 | **租户企业采购部**；下游主机厂客户；上游配件/冲压等供应商（文案不绑定具体商号） |
| 主用户 | **采购员 + 采购主管**；核价/销售/管理层为扩展受众 |
| 交互 | **壳层浮动聊天助理** + REST 完整报告 + 异步轮询；无流式；**不挂侧栏菜单**（C13） |
| 模板 | 胶囊 → 固定 `report_type`；自由输入 → `auto` 规则解析，默认 `dashboard`；**均发请求**（C3） |
| 对话历史 | **仅 localStorage**（按用户+scope 分 key）；后端无多轮 Session |
| 报告价值 | 说清付多少、涨在哪、缺什么价、下一步催谁；不自动议价 |
| 分析主线 | **年数据齐套 + 月链变动 + L0 分层归因**（§4）；月动看①/钢材，年侧看②③④ |
| 喂数 | Context Pack；KPI+TopN+异常；比率在 Aggregator 由 VO 汇总或上游 Service 提供 |
| 取数通道 | **仅上游 Service**（C12）；禁止 llm 直连结果表 Repository / 另建查数工具 |
| 字段真相 | **现网 Pydantic VO Schema** + 受控中文覆盖（§4.7）；禁止分析侧另造字段让模型猜 |
| 金额单位 | **元**；**禁止改为万元**（C10） |
| 异常分析 | Pack 有风险必出专节；无则明示未见（C11 / §7.5） |
| 输出契约 | `AnalysisReportTaskVO` / `AnalysisReportVO`（§6） |
| 幂等 | scope+type+audience+**问题指纹**+TTL；`force_refresh`（§10.2） |
| 版本 | `prompt_version` + `prompt_hash`（§10.3） |
| 与引擎 | 消费结果与 Run；硬停仅 `gate` |
| 切片落点 | **独立 `llm` 切片**（不进 costing）；目录见 §5.1.1～§5.1.2 |
| 前端壳 | 专用目录 `static/js/llm-assistant/`；顶栏帮助左侧机器人；`z-index:110`；就绪队列；DOMPurify；docked 右/底 |

---

## 14. 参考文件索引

**参考项目**：`aggregator-service.ts`、`chat-prompts.ts`、`field-labels` 思路  

**本仓库**：`docs/costing-engine-design.md`、`docs/l0-assembly-costing-design.md`、`tests/costing/last_qingdao_t28_sim_report.txt`、`app/models/costing/*`、现网 AsyncTask 进度 VO  

---

## 15. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-22 | 初稿：Context Pack + 参考 MCP 模式 |
| 2026-08-22 | **REST 定稿修订**：移除流式/对话主路径假设；补异步任务、Report VO 契约、幂等、Prompt 版本；主路径改为固定 `report_type` |
| 2026-08-22 | **采购角色修订**：明确本公司→主机厂、采购←供应商价值链；增补 §1 / §1A 多角色关注点；报告模板与 Prompt 改为采购决策口吻；`audience` / `exec_brief` |
| 2026-08-22 | **商号中立**：去除具体企业/主机厂名；增 C7，便于产品对外售卖 |
| 2026-08-22 | **架构目录**：补 §5.1 分层图与前后端拟新增文件树、协作时序、配置项 |
| 2026-08-22 | **切片隔离**：LLM 从 costing 拆出为独立 `llm` 垂直切片（API/目录/表/权限） |
| 2026-08-22 | **对话 UX**：前端改为对话壳 + §9.2 常见提问；**对话历史仅 localStorage**（C8） |
| 2026-08-22 | **分析主线**：重写 §4——年数据 / 月数据 / 核算分层（0～4）内容与归因逻辑 |
| 2026-08-22 | **Schema 约束**：增 C9 与 §4.7——复用现网 VO 作字段真相，schema_card 注入 Prompt 防瞎想 |
| 2026-08-22 | **单位与异常**：增 C10/C11、§7.5；落地 `app/services/llm/prompts/`（含禁止万元、异常专节） |
| 2026-08-22 | **取数约束 C12**：业务数据只经上游 Service；取消 llm aggregate_repository / 独立查数工具设计 |
| 2026-08-22 | **SchemaCatalog 落地**：`catalog/schema_catalog.py` + `field_labels.py`；单测 `tests/llm/test_schema_catalog.py` |
| 2026-08-22 | **Service 分包定稿**：`catalog` / `context` / `analysis` / `prompts` / `client` / `export`；禁止包根平铺 |
| 2026-08-22 | **自由输入也发请求（C3 修订）**：`user_question` 必填；`report_type=auto` + 规则解析 / 默认 `dashboard`；禁止本地拒答不调 API |
| 2026-08-22 | **前端壳层助理（C13）**：帮助左侧机器人；浮动窗 / 最大化 / 最右侧小气泡；不挂侧栏菜单、不抢镜头 |
| 2026-08-22 | **壳层工程补强 §9.1.1**：z-index=110（低于 Toast）；遮罩不压暗业务；`LlmAssistant` 就绪队列；DOMPurify；docked&lt;768 底部降级 |
| 2026-08-22 | **前端专用目录**：全部壳层代码收拢 `static/js/llm-assistant/`；不进 `features/`、不进侧栏 |

---

*本文仅设计。实现前以 §13 决策摘要开任务；产品评审优先对齐 §1A 角色矩阵与 **C13 壳层助理**；工程按 §5.1.1～§5.1.2 建目录后落地 §5.2～§6 与 §10.2～§10.3。*
