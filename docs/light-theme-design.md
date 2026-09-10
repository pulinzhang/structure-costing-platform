# 浅色主题改造 — 设计说明

> 状态：**已否决（不做）**  
> 决定：2026-08-28。产品立场：**冷艳、不退让。** 维持 Brabus Carbon 深色；不上浅色、不写 `brabus_theme`、不改前端代码。  
> 下文是否决前的设计与工作量评估，仅作存档。若以后有人再提「有人不习惯深色」，先读本节，不要当成漏做的需求。  
> 关联：`.cursor/rules/front-end.mdc`

---

## 0. 一句话（否决结论）

> **不改。** 这套核价台就是碳素黑、钛灰、标志红。不因为「以前软件都迁就用户」就加一套浅色。

对标的是 **IntelliJ、Cursor 这类专业工具的默认脸**：深色、冷、长时间盯数据。不是 Word / 用友那种办公白。IDE 里浅色主题是附属，不是身份。本台连附属也不做。

不引入双主题、不改 token、不在个人资料加外观开关。不习惯的人适应界面，而不是界面改成通用办公白。

否决前曾评估过语义色 + `brabus_theme` + 全站换皮（约 6–8 周）。**不是因为工期做不起，是因为品牌不让。** 下文方案只作存档。

---

## 1. 为什么曾有人要改

现网是 **Brabus Carbon & Precision Dark**：碳素黑底、钛灰面板、标志红。部分使用场景（白天办公、投影、打印预览）不适应长时间深色。

现网 **已经有** `:root` 变量（`--bg-deep`、`--text-main` 等），但业务页几乎不走变量，颜色写死在 class 和内联 style 里。只改 `style.css` 的 `:root`，结果是：壳层可能变浅，表格 / 登录 / 抽屉 / Toast 仍是黑的。

### 1.1 现网规模（盘点，2026-08）

| 量 | 规模 |
|----|------|
| `static/` 文件 | 116 |
| hex 出现次数 | 约 6600 |
| 不重复色值 | 约 200 |
| Tailwind `bg-[#…]` | 约 1313 |
| Tailwind `text-[#…]` | 约 3181 |
| Tailwind `border-[#…]` | 约 1378 |
| 内联 `style=` | 约 513 |
| 真正使用 `var(--…)` | 约 94（几乎全在壳层 CSS） |

色值最密的是 HUD 列表模板（冲压加工费、钢材联动、成品焊接费、零件价格一览等），单文件 200–370 处。行 HTML 往往在对应 `index.js` 再写一遍同样的 hex。

### 1.2 约束（决定了不能怎么做）

| 约束 | 含义 |
|------|------|
| 无构建步骤 | 不能靠 Tailwind `dark:` 变体或编译期 theme |
| Tailwind CDN + 任意值 hex | `bg-[#0a0a0a]` **不会**随 CSS 变量切换 |
| 规范禁止浅底 | 现 `front-end.mdc` 明确禁止 `bg-white` / `bg-slate-50` 等；落地前必须改规范 |
| 两套红 | `#d32f2f`（壳层）与 `#FF1E27`（HUD）页内已要求只选一种；浅色同样 |

### 1.3 禁止的做法

| 做法 | 为什么不行 |
|------|------------|
| 只改 `:root` | 业务页仍是 hex，观感割裂 |
| 每个 class 写 `bg-[#0a0a0a] light:bg-[#F4F4F5]` | 6600 处不可维护 |
| 全局 find-replace 黑→白 | `#555555` 有的是表头、有的是禁用、有的是占位；HUD glow 反相后发脏 |
| 只改壳层 / 登录 | 顶栏浅、表格仍黑，比现在更差 |
| 改成大圆角浅色 SaaS | 违背工业密表，等于重做一套设计语言 |

---

## 2. 改造目标

| # | 目标 |
|---|------|
| G1 | **深色与浅色并存**，同一套组件，只换 token |
| G2 | 品牌红仍是唯一强调色；表体直角、密表、等宽数字、操作只走操作列 |
| G3 | 颜色进入语义 token；**所有** `template.js` / 行渲染 `index.js` 不再写业务 hex |
| G4 | 浅色 HUD：**实心红 + 淡红底 KPI 列**，去掉 `text-shadow` / 霓虹 glow / 大块黑阴影；深色 HUD 可保留现网发光 |
| G5 | **前端每一面**（下表 §3.1 全量）读同一 `brabus_theme`；禁止某页仍写死深色 |
| G6 | 选择只存在本机 `localStorage`，不进用户表、不进 API |
| G7 | 落地时只改 `.cursor/rules/front-end.mdc`（规范正文只此一处） |

后端、权限码、Hash 路由名、API 契约 **不在目标内**。不改功能，只换皮。

---

## 3. 范围：前端全量（无豁免）

对照现网 `features/index.js` 的 `pageMeta`（40 条）+ `app.js` 的 `pages` + 独立 HTML。别名 `#/bom`、`#/bom-list`、`#/login` 只跳转，不另做一页。

### 3.0 全站改是不是必要？会不会更难看？

两件不同的事，不要混：

| 担心 | 实际 |
|------|------|
| 不改某页，只靠 `brabus_theme` | **无效。** 键只改 `html[data-theme]`。`bg-[#0a0a0a]` 不会跟着变。没改的页永远是深色。 |
| 全站改完，浅色会不会丑 | **有可能。** 那是浅色色板 / HUD 去 glow 的设计问题，不是 token 化本身。 |

因此：

1. **只要个人资料里能切浅色，前端每一面都必须走 token。** 只改壳层和几个表，用户一切浅色就是「顶栏白、中间表还是黑」——这比现在全深色难看得多。`brabus_theme` 不能当「改一半」的借口。
2. **Token 化不等于把深色毁掉。** `:root` 仍映射现网深色 hex，默认 `dark` 时，改完的页应和现在几乎一样。难看风险主要在浅色，不在深色。
3. **浅色好不好看，P1 一页就能否决。** 零件价格一览 + 壳层 + 登录，浅色若发飘、发脏、表格看不清 → **停，不进 P2。** 不要把一套没过关的浅色铺到 40 页。
4. **可以不做浅色。** 若 P1 否决，或决定继续全员深色：不发布外观卡，不写 `brabus_theme` 切换。已做的 token 仍可留着（深色映射现网），不算白做，只是没有第二套皮。

**完成定义：** 若发布双主题，下表每一行在深色、浅色下都可读、可操作；对应 `template.js` 与会拼 HTML 的 `index.js` 成对改完。漏一行 = 未完成。

### 3.1 覆盖清单

#### A. 主应用壳（所有 Hash 页共用）

| 面 | 文件 | 阶段 |
|----|------|------|
| 入口 / body | `static/index.html` | P1 |
| 侧栏 Overlay、顶栏、面包屑、用户菜单 | `style.css`、`index.html`、`login/index.js` 的 `initUserMenu` | P1 |
| Toast | `main.js` | P1 |
| 分页条 | `page-size.js` | P1 |
| AI 助理（浮动层，跟页走） | `llm-assistant/**`（含历史、聊天、打印预览、Word 导出样式） | P3 |

#### B. 登录（独立页，无侧栏）

| Hash / URL | 标题 | 阶段 |
|------------|------|------|
| `/login` | 系统登录 | P1 |

文件：`login.html`、`features/login/template.js`。无主题开关，只读 `brabus_theme`。

#### C. Hash 业务页（40）

阶段：**P1** 试点 2 页；**P2** 其余列表；**P3** 上传/计算/特殊。

**仪表盘**

| Hash | 标题 | 阶段 |
|------|------|------|
| `#/dashboard` | 仪表盘 | P3 |

**冲压工程（6）**

| Hash | 标题 | 阶段 |
|------|------|------|
| `#/stamping-upload` | 上传工艺文件 | P3 |
| `#/stamping-parts` | 冲压零件列表 | P2 |
| `#/stamping-tonnage-upload` | 冲次单价上传 | P3 |
| `#/stamping-tonnage` | 冲次单价列表 | P2 |
| `#/stamping-process-fee-calc` | 冲压加工费计算 | P3 |
| `#/stamping-process-fee` | 冲压加工费列表 | P2 |

**焊接工程（14）**

| Hash | 标题 | 阶段 |
|------|------|------|
| `#/bom-upload` | 上传材料清单 | P3 |
| `#/bom-material` | 材料清单列表 | P2 |
| `#/bom-structure` | 产品结构 | P3 |
| `#/bom-viz` | 产品结构图 | P3 |
| `#/bom-welding-unit-price-upload` | 焊接单价上传 | P3 |
| `#/bom-welding-unit-price` | 焊接单价列表 | P2 |
| `#/bom-annual-part-price-upload` | 年度零件价上传 | P3 |
| `#/bom-annual-part-price` | 年度零件价列表 | P2 |
| `#/bom-packaging-transport-fee-upload` | 包装运输费上传 | P3 |
| `#/bom-packaging-transport-fee` | 包装运输费列表 | P2 |
| `#/bom-welding-process-breakdown` | 焊接工艺拆解 | P3 |
| `#/bom-welding-process-breakdown-list` | 焊接工艺拆解列表 | P2 |
| `#/bom-welding-fee-calc` | 焊接费计算 | P3 |
| `#/bom-welding-fee-list` | 焊接费列表 | P2 |

**一事一议（6）**

| Hash | 标题 | 阶段 |
|------|------|------|
| `#/steel-price-policy-upload` | 加减价政策上传 | P3 |
| `#/steel-price-policy-download` | 加减价政策列表 | P2 |
| `#/base-price-upload` | 基准价格上传 | P3 |
| `#/base-price-download` | 基准价格列表 | P2 |
| `#/winning-thickness-download` | 中标钢厂厚度价格一览表 | P2 |
| `#/scrap-price` | 废料月度销售价 | P2 |

**主数据**

| Hash | 标题 | 阶段 |
|------|------|------|
| `#/steel-grade-category` | 牌号分类 | P2 |

**核价（7）**

| Hash | 标题 | 阶段 |
|------|------|------|
| `#/steel-price-calc` | 冲压钢材联动计算 | P3 |
| `#/steel-price-list` | 冲压钢材联动价一览 | P2 |
| `#/stamping-part-cost-calc` | 冲压零件价格计算 | P3 |
| `#/stamping-part-cost` | 冲压零件价格一览 | **P1 标杆** |
| `#/l0-assembly-cost-calc` | 成品核价计算 | P3 |
| `#/l0-assembly-cost` | 成品核价一览 | P2 |
| `#/costing` | 自动核价引擎 | P3 |

**文件溯源 / 设置（5）**

| Hash | 标题 | 阶段 |
|------|------|------|
| `#/file-trace` | 文件溯源 | P2 |
| `#/settings` | 系统设置 | P3 |
| `#/settings-users` | 用户管理 | P2 |
| `#/settings-logs` | 操作日志 | P2 |
| `#/settings-profile` | 个人资料（含外观卡） | **P1** |

合计 Hash **40**，与 `pageMeta` / `pages` 一致。

#### D. 帮助站（5，独立 HTML，不用 Tailwind）

| URL | 标题 | 阶段 |
|-----|------|------|
| `/static/helper/index.html` | 使用帮助入口 | P3 |
| `/static/helper/help.html` | 帮助 | P3 |
| `/static/helper/knowledge.html` | 知识库 | P3 |
| `/static/helper/example.html` | 样例 | P3 |
| `/static/helper/print-all.html` | 整本打印 | P3 |

每页防闪脚本 + 共享 `theme-tokens.css`。无开关。

#### E. 页内二次面（随所属页一起改，P4 仍要点）

抽屉、详情、确认框、预览表、计算历史分页、上传进度、引擎步骤条、用户编辑弹层、结构图节点色。只改 `template.js` 不算完，`index.js` 里拼的 HTML 必须同期改。

### 3.2 不做

| 不做 | 说明 |
|------|------|
| 后端 / 数据库 / API | 主题是纯前端 |
| 权限、路由名、侧栏信息架构 | 只换皮 |
| 为主题引入构建链 / 换 UI 框架 | 继续 Tailwind CDN + 原生 JS |
| **任何页面豁免 / 历史页「以后再说」** | §3.1 全量；P4 按表打勾，缺一页不算发 |
| 浅色上保留暗色霓虹 HUD | 见 §5.3；深色可以留 |
| 主题跟账号 / 服务端配置 | 只认本机 `localStorage`，登出不清主题 |
| 顶栏 / 登录页放主题开关 | 入口只在个人资料；顶栏保持现网信息密度 |
| 主题写入 `PUT /api/auth/me` | 本机记忆，不进用户资料接口 |
| 跟随系统 `prefers-color-scheme` | 不做自动跟随，避免和本机记忆打架 |

### 3.3 拍板记录

| # | 问题 | 结论 |
|---|------|------|
| D0 | 做不做？ | **否决。** 保持冷艳，不向浅色退让。2026-08-28 |
| D1 | 深色与浅色？存在哪里？ | （否决前方案）两套都在。本机 `localStorage`，键 `brabus_theme` |
| D2 | 浅色 HUD 是否去掉霓虹发光？ | （否决前方案）浅色去掉；深色保持 |
| D3 | 先试点还是一次全量？ | （否决前方案）先试点再全量；P1 视觉否决 |

否决前工期估算：约 **6–8 周**（1 人全职）。**不执行。**

---

## 4. 设计语言：同一套结构，两套色板

理念三句话不变：**极简克制、工业精密、红色唯一强调**。深色继续是 Carbon Dark；浅色是同一骨架上的 Precision Light，不是另一套后台皮肤。

切换只改 `html[data-theme]`，**不改 DOM 结构**。glow / 重阴影用 token 表达，浅色上把它们收成「无 / 轻」。

### 4.1 色板

名称用语义，不要用 `gray-500` 这种与 Tailwind 默认冲突的名字。  
**`:root` = 深色**（与现网一致，无 JS 时也不闪浅）。`html[data-theme="light"]` 覆盖为浅色。

#### 浅色 `html[data-theme="light"]`

| Token | 浅色 hex | 用途 |
|-------|----------|------|
| `--bg-canvas` | `#F4F4F5` | 页面最底层。略暖灰白，**禁止**整页纯 `#FFFFFF` |
| `--bg-surface` | `#FFFFFF` | 卡片 / 抽屉 / 设置面板 |
| `--bg-table` | `#FFFFFF` | HUD 表外框（浅色可与 surface 同值，**键必须在**） |
| `--bg-elevated` | `#FAFAFA` | 输入、表头条 |
| `--bg-raised` | `#FAFAFA` | Toast / 悬浮 |
| `--bg-hover` | `#F4F4F5` | 表行 hover（浅底上略深一档即可） |
| `--bg-kpi` | `#FEF2F2` | 关键金额列、本期均价卡 |
| `--text-main` | `#18181B` | 主文字、零件号 |
| `--text-muted` | `#52525B` | 标签、表头 |
| `--text-dim` | `#71717A` | 次行说明、占位 |
| `--text-numeric` | `#3F3F46` | 表格数字（浅底上比暗色 `#8E8E93` 更深，避免发飘） |
| `--border-subtle` | `#E4E4E7` | 行分割、弱线 |
| `--border-color` | `#D4D4D8` | 面板边、输入框 |
| `--border-active` | `#d32f2f` | focus / 激活 |
| `--brabus-red` | `#d32f2f` | 主按钮、激活条、关键数字 |
| `--brabus-red-hover` | `#b71c1c` | 主按钮 hover |
| `--success` | `#15803D` | 浅底上略深于现网 `#2e7d32` / `#4caf50` |
| `--warning` | `#C2410C` | 浅底警告 |
| `--danger` | `#B91C1C` | 浅底错误（与品牌红同族，饱和度略收） |

**页内品牌红只保留 `#d32f2f`。** HUD 现用的 `#FF1E27` 收到 `--brabus-red`，禁止同一表混两套红。

#### 深色 `:root` / `html[data-theme="dark"]`（现网映射）

| Token | 深色 hex | 对应现网 |
|-------|----------|----------|
| `--bg-canvas` | `#0a0a0a` | `--bg-deep` / `body` |
| `--bg-surface` | `#1e1e1e` | 普通卡片 / 抽屉 / 设置页面板 |
| `--bg-table` | `#0A0A0C` | HUD 表外框（**必拆**，勿与 `--bg-surface` 混用） |
| `--bg-elevated` | `#0a0a0a` | 输入底（抬升面板深色用 `#262626` 时走 `--bg-raised`，见下） |
| `--bg-raised` | `#262626` | Toast / 悬浮 / 次级槽 |
| `--bg-hover` | `#161620` | 表行 hover |
| `--bg-kpi` | `#1A080A` | KPI 暗红底 |
| `--text-main` | `#F0F0F2` | 主文字 |
| `--text-muted` | `#555555` | 表头 |
| `--text-dim` | `#616161` | 次要 / 禁用 |
| `--text-numeric` | `#8E8E93` | 表格数字 |
| `--border-subtle` | `#141418` | 行分割 |
| `--border-color` | `#2c2c2c` | 面板边 |
| `--border-active` | `#ff5252` | focus |
| `--brabus-red` | `#d32f2f` | 品牌红（HUD 的 `#FF1E27` 收口到此） |
| `--success` / `--warning` / `--danger` | 现网状态色 | 可保持 |

还要为壳层与半透明红准备下列 token（两套主题都赋值），否则侧栏 / HUD 按钮无法只靠上面那张表落地：

| Token | 用途 |
|-------|------|
| `--overlay` | 侧栏遮罩 |
| `--sidebar-text` / `--sidebar-text-muted` | 导航字色（深色是半透明白，浅色是实色深字） |
| `--shadow-frame` / `--shadow-kpi` / `--text-glow-kpi` | 外框阴影、KPI 光；浅色上后两项为 `none` |
| `--brabus-red-soft` | 红 10% 底（按钮 hover、徽章），**不要**写 `bg-[var(--brabus-red)]/10` |
| `--brabus-red-ring` | 红 20%–50% 边 |

### 4.2 组件对照

| 要素 | 暗色（现网） | 浅色 |
|------|--------------|------|
| 画布 | `#0a0a0a` | `--bg-canvas` |
| 表外框 | `#0A0A0C` + 重黑阴影 | 白底 + `--border-color` + **轻**灰阴影 |
| 表头 | `#555555` / 9px | `--text-muted`，字号规则不变 |
| 主信息 | `#F0F0F2` 加粗 | `--text-main` 加粗 |
| 数字 | 右对齐等宽 `#8E8E93` | 同结构，色走 `--text-numeric` |
| KPI 列 | 暗红底 + 霓虹字 + glow | `--bg-kpi` + `--brabus-red` 实心字，无 text-shadow |
| 行 hover | `#161620` + 左 2px 红条 | `--bg-hover` + 同样左红条（条保留） |
| 主按钮 | `#d32f2f` / 白字 | 不变 |
| 次按钮 | 透明 + 灰边 | 白底 + `--border-color` + `--text-muted` |
| 输入 / 下拉 | `#0a0a0a` 底 | `--bg-elevated`，深字 |
| 侧栏 | 炭黑渐变 + 半透明白字 | `--bg-surface` + `--text-main`；激活仍左红条 |
| 顶栏 `.page-header` | `#111114` | `--bg-surface` + 细边 |
| Toast | `#1e1e1e` + 重阴影 | `--bg-raised` + 细边 + 轻阴影 |
| 空状态 | 弱灰图标 | `--text-dim` 图标 + `--text-muted` 标题 |
| 滚动条 | 白 7% 透明 | 深色 20% 透明，细条仍 4px |
| 选区 `::selection` | 红 glow + 白字 | 浅红底 + `--text-main` |

圆角规则不变：控件 `rounded` / `rounded-sm` / `rounded-md`；**表体与面板保持直角**。禁止 `rounded-lg+`、禁止 Bootstrap、禁止浅色蓝主色。

### 4.3 规范条文要改什么（落地时，不是现在）

现规范「禁止 `bg-white` / `bg-slate-50`」改为：

- 画布必须用 `--bg-canvas`（灰白），禁止整页纯白无边框铺满。
- 面板允许白底，但必须带 `--border-color`。
- 业务 class 仍禁止写入 `style.css`；颜色必须走 token，禁止新增业务 hex。
- 页内强调红只许 `--brabus-red`（`#d32f2f`），深浅皆然。
- `--bg-table`、`--bg-raised`、`--overlay`、`--shadow-*`、`--brabus-red-soft` 必须进规范速查，禁止再发明页内私有色。

规范正文只改 `.cursor/rules/front-end.mdc`。

---

## 5. 技术设计

### 5.1 Token 如何进 Tailwind（钉死写法 A）

无构建，只能让 **class 引用变量**。全站只用 **A**，不用 B：

```html
<div class="bg-[var(--bg-table)] text-[var(--text-main)] border-[var(--border-color)]">
```

| 不选 B 的原因 | 说明 |
|---------------|------|
| `border-color` 会和 CSS 属性撞名 | `theme.extend.colors` 里叫 `color` / `main` 也容易和现网 class 打架 |
| `index.html` 与 `login.html` 各写一份 `tailwind.config` | 两份会漂 |
| 帮助站不用 Tailwind | token 必须活在 CSS 文件里，不能只活在 CDN config |

**禁止** `bg-[#0a0a0a]` 当业务底色。红底按钮上的 `text-white` **允许**。

**Tailwind 透明度修饰不能用在 CSS 变量上。** `border-[var(--brabus-red)]/50`、`hover:bg-[var(--brabus-red)]/10` 在 CDN 下不可靠。半透明红一律改成实色 token（`--brabus-red-soft`）或 `color-mix(in srgb, var(--brabus-red) 12%, transparent)` 写进变量。

阴影不要用 `shadow-[0_4px_24px_rgba(0,0,0,0.7)]`：任意值阴影不会随主题变。用 `style="box-shadow: var(--shadow-frame)"` 或壳层 class。

壳层 CSS（`.sidebar`、`.page-header` 等）去掉写死 hex / `rgba(255,255,255,0.08)`，改为 `var(--…)`。不要为单个业务页往 `style.css` 加 class。

建议拆文件：`static/css/theme-tokens.css`（只有 `:root` 与 `[data-theme="light"]`）被 `style.css` 与 `helper/helper.css` 同时引入，避免帮助站和主站两套 token。

### 5.2 主题挂载与本机记忆（一期就要做）

**真相在 `html` 属性，记忆在 `localStorage`。** 不读系统配色，不写数据库。

| 项 | 约定 |
|----|------|
| 属性 | `html[data-theme="dark" \| "light"]` |
| 存储键 | `brabus_theme`（与现网 `brabus_user`、`brabus_operator_id` 同前缀） |
| 合法值 | 仅 `"dark"` / `"light"`；其它或损坏视为无记录 |
| 无记录默认 | **`dark`**（与现网一致，老用户不被突然洗成浅色） |
| 作用域 | 本浏览器、本源。换电脑 / 清站点数据会丢，需再选一次 |
| 与登录 | **登出不清** `brabus_theme`。换账号共用这台机器上的选择 |
| 入口 | `index.html`、`login.html`、帮助站共用同一键 |

#### 防闪（阻塞脚本，放在 Tailwind / `style.css` 之前）

```html
<script>
(function () {
  var k = 'brabus_theme';
  var t = 'dark';
  try {
    var s = localStorage.getItem(k);
    if (s === 'light' || s === 'dark') t = s;
  } catch (e) {}
  document.documentElement.setAttribute('data-theme', t);
})();
</script>
```

无这段脚本时 CSS `:root` 已是深色，最坏也只是「该浅却先闪一下深」，不会浅→深闪瞎。

脚本允许在 `index.html`、`login.html`、帮助站各 `*.html` **原文复制**（阻塞、无依赖）。不要改成 import，否则会闪。

#### 切换（入口只在个人资料）

- **唯一操作入口**：`#/settings-profile` 个人资料页。现网该页是「身份摘要 + 基本资料 + 安全设置」；新增独立卡片 **「外观」**，不要塞进「基本资料」表单（那张卡要点保存才生效，主题必须立刻换）。
- 建议位置：三列网格下方通栏卡片（与改密物理隔离）；卡片内两项：**深色 / 浅色** 分段选择（或 radio），当前项高亮品牌红。不要只放无文字的月亮图标。
- **立刻生效**：点选即 `applyTheme(...)`，**没有「保存」按钮**，不调 `PUT /api/auth/me`。
- 权限：`menu:settings-profile` 在权限设计里对所有角色是**强制**菜单，能登录就能进个人资料，因此**不新增权限码**。外观卡不要挂 `op:settings-profile:update`。
- **顶栏、登录页、帮助站都不放开关。** 它们只在加载时读 `brabus_theme` 上色。未登录用户看到的是这台机器上次选的（默认深色）。
- 行为：`setAttribute('data-theme', …)` + `localStorage.setItem('brabus_theme', …)`，并 `dispatchEvent(new Event('brabus-theme'))`（结构图监听后重绘）。隐私模式写入失败时仍切换当次会话，Toast「无法记住主题」。
- 实现：`static/js/theme.js` 作 ES Module，导出 `applyTheme` / `getTheme`。个人资料 `index.js` `import`。禁止各页直接读写 `localStorage`。`main.js` 不要再实现一套。
- 改脚本后必须递增相关 `?v=`（`app.js` 对 profile 的 import、profile 对 `theme.js`）。
- 帮助站只靠防闪脚本 + `theme-tokens.css`，不加载 `theme.js`。

#### 结构图 / 内联色

`bom/material/viz` 等用 JS 写 `fill` / `stroke` 的，切换主题时必须重绘或改节点色。不要假设只刷 CSS 变量就够。

`body` 不要再写 `bg-[#0a0a0a]`，改为 `bg-[var(--bg-canvas)]` 或等价语义 class。

### 5.3 不能只换 token 的部分（浅色必须重画；深色可近似现网）

这些依赖「深底 + 发光」，映射到浅色变量会很难看，要按 §4.2 改结构或内联阴影：

| 部位 | 现网手法 | 浅色做法 |
|------|----------|----------|
| HUD 外框 | `box-shadow: 0 4px 24px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.02)` | 轻灰外阴影，去掉假高光 inset |
| KPI 卡渐变 | `from-[#18080A] to-[#0D0708]` + 顶红光条 | 白/淡红底，顶条可用 2px `--brabus-red`，不要 glow |
| 均价数字 | `text-shadow: 0 0 12px rgba(255,30,39,…)` | 删除 text-shadow |
| 侧栏 | `linear-gradient(180deg, #121214, #080809)` | 纯 `--bg-surface` 或极弱灰竖向梯度 |
| 遮罩 | `rgba(0,0,0,0.75)` | 可保留深遮罩（浅色 UI 上深遮罩仍合理） |
| 结构图节点 | 为深底调的灰 / 铜 / 蓝灰 | 提高对比、加深描边；不要 `lightenHex` 到接近白 |
| WebKit autofill | inset 暗底 | inset `--bg-elevated` + `--text-main` |

### 5.4 文件改造策略

按 §3.1 的阶段扫，**不要**按 hex 全局替换，也**不要**只改「看起来像标杆的列表」。

1. **P1 壳层 + 登录 + 个人资料 + 零件价格一览**（定词典）  
2. **P2 §3.1 全部其余列表**（含一事一议矩阵、牌号分类、溯源、用户、日志）  
3. **P3 全部上传 / 计算 / 仪表盘 / 结构 / 结构图 / 引擎 / 系统设置**  
4. **P3 全局残留**：LLM 助理、帮助站 5 页、导出打印  

同一语义在 `template.js` 与 `index.js` 行渲染必须一起改。抽屉、确认框算所属 Hash 页的一部分。

### 5.5 验收（前端目视，无单测要求）

**P4 按 §3.1 逐行打勾**，不是抽检。每个 Hash 页深色、浅色至少：

- 有数据 / 空 / 加载（没有空态的页走主路径即可）  
- 有筛选、分页的：筛一次、翻页、改每页条数  
- 有抽屉/弹层的：从**操作列**打开（禁止整行点击进明细）  
- 上传/计算页：表单、主按钮、进度或历史区  
- 结构图：切主题后节点仍可读（`brabus-theme` 重绘）  
- 引擎：步骤条/状态色两套都对  

另外必验（不算 Hash，但算前端）：

- `/login`、帮助站 5 个 HTML、Toast、侧栏开合、AI 助理开/收/历史  
- 刷新、登出再登录，主题仍在  

漏 §3.1 任何一行 = 不能合生产。

### 5.6 可落地性（对照现网，2026-08）

**结论：能落地；范围是前端全量 40 Hash + 登录 + 帮助 5 页 + 壳层/Toast/助理。** 不能按「先上开关再慢慢改页」发生产。Token 化期间若用户已切浅色，未改页仍是写死深色。外观卡分支内 P1 可用，**合入生产门槛：§3.1 每一行都走 token**。

| 现网事实 | 对落地的含义 |
|----------|----------------|
| 无构建 + Tailwind CDN + 约 6600 hex | 只能 `bg-[var(--token)]`，工作量在扫文件，不在新架构 |
| `:root` 已有变量但业务不用 | 先扩 token 文件，再替换 class，不能只改 `style.css` |
| HUD 列表约 14 个 `list/template.js`，且同构 | 标杆页（零件价格一览）定 class 词典后，其余是复制劳动 |
| 行 HTML 在对应 `index.js` | 每次改 template 必须同时改 index，否则半套主题 |
| 个人资料 `menu:settings-profile` 全角色强制 | 开关放这里所有登录用户都找得到；不必新权限 |
| 登录是独立 `login.html` | 必须复制防闪脚本；无开关，只读存储 |
| 帮助站是独立 `helper.css`，不用 Tailwind | 必须共享 `theme-tokens.css` + 各 html 防闪；打印发黑可二期再 `@media print` 强制浅 |
| 入口脚本 `?v=` 缓存 | 每改 `theme.js` / 模板 / CSS 都要加版本号，漏了用户会以为没改 |
| 登出只清 `brabus_user` | `theme.js` 与 login 清会话代码要互相避开 `brabus_theme` |

**会翻车、必须事先避开：**

1. `hover:bg-[#FF1E27]/10` 这类 `/透明度` 不能直接换成 CSS 变量版。  
2. `--bg-surface` 不能同时表示 `#1e1e1e` 卡片和 `#0A0A0C` 表框。  
3. 结构图、引擎进度条、Toast、LLM 助理若最后才改，验收会判「没做完」。  
4. 半成品合进生产并打开外观卡。

---

## 6. 实施计划

一人全职。开发在独立分支，**P4 合入前不把外观卡发到生产**（分支内可以从 P1 打开，供目视）。

### P0 — 冻结规范与 token（约 3 人天）

| 交付 | 完成标准 |
|------|----------|
| 两份 `front-end.mdc` 按本文改完 | 允许浅色面板；禁止业务 hex；写法 A；红收口 `#d32f2f` |
| `theme-tokens.css`：深色 `:root` + `html[data-theme="light"]` | 每个 token 两套都有值；含 table / raised / overlay / shadow / red-soft |
| `theme.js` + 三处防闪脚本（主站、登录、帮助入口） | 无记录为 dark；非法值回退 dark |

**出口：** 手工设 `localStorage.brabus_theme=light` 刷新，壳层尚未改时仍大部分是深色——这是预期；此阶段只保证属性挂上、不报错。

### P1 — 试点（约 4–6 人天）

范围：**壳层**（`style.css` 侧栏/顶栏/滚动条/autofill）+ **登录页** + **个人资料外观卡** + **零件价格一览**（`template.js` 与 `index.js` 一起）。

| 交付 | 完成标准 |
|------|----------|
| 外观卡 | 网格下方通栏；深/浅立刻切换；无保存；不调 API |
| 标杆 HUD | 浅色无 glow；深色观感接近现网 |
| 登录 | 随本机主题，无开关 |

**出口：** 个人资料来回切 10 次不闪、刷新保持；零件价格一览两套都能看表、开抽屉、分页。**浅色若发脏、对比不够、表格难看 → 在此否决，不进 P2。** 通过后其余页只复用标杆词典，禁止另发明一套浅色。

### P2 — 其余全部列表（约 10–12 人天）

§3.1 标了 P2 的 **每一页**，不是「优先几个」：

冲压零件、冲次单价、冲压加工费、钢材联动一览、成品核价一览、成品焊接费、焊接单价、年度零件价、包装运输费、焊接工艺拆解列表、材料清单、加减价政策列表、基准价格列表、中标厚度一览、废料月度价、牌号分类、文件溯源、用户管理、操作日志。

标杆 class 词典复制；`template.js` + `index.js`（含抽屉）成对。

**出口：** 上列每一页深/浅主路径过一遍；无「只改了表头、行还是 hex」。

### P3 — 其余全部业务 + 全局层（约 8–10 人天）

§3.1 标了 P3 的 **每一页**：

- 上传：工艺、冲次单价、政策、基价、BOM、焊接单价、年度零件价、包装运输费  
- 计算/生成：加工费、钢材联动、零件价格、成品核价、焊接工艺拆解、成品焊接费  
- 特殊：仪表盘、产品结构、产品结构图（`brabus-theme` 重绘）、自动核价引擎、系统设置  
- 全局：AI 助理全套、帮助站 5 个 HTML、`export/print.js` / Word 若写死色  

**出口：** `pageMeta` 40 条 + `/login` + 帮助 5 页，浅色下无大面积写死深色 hex。

### P4 — 验收与合入（约 6–8 人天）

- 按 §3.1 **逐行**深/浅打勾（含抽屉、空态、助理、帮助）  
- 刷新、关标签再开、登出再登录，主题仍在  
- 隐私模式：能切、Toast 无法记住  
- 递增所有改过的 `?v=`  
- 合入生产，外观卡对用户可见  

**回滚：** 只删外观卡不够（token 已替换）。回滚应整分支回退；或临时把 light 块改成与 dark 相同（应急，不作为设计）。

### 6.1 人天汇总

| 阶段 | 人天 |
|------|------|
| P0 规范 + token + theme.js | 3 |
| P1 试点（壳 + 登录 + 资料 + 标杆一览） | 4–6 |
| P2 其余全部列表 | 10–12 |
| P3 其余全部页 + 助理 + 帮助 | 8–10 |
| P4 全表打勾验收 | 6–8 |
| **合计** | **约 31–39 人天（6–8 周）** |

比「只做核价 HUD」更长：一事一议矩阵、牌号分类、溯源、用户/日志、全部上传计算、帮助 5 页、助理都在范围内。

### 6.2 风险（实施时对着查）

- **语义误分类**：同一 `#555555` 不能全局替换成一个 token。  
- **漏改 `index.js`**：模板浅了、行渲染仍黑。  
- **半成品合生产**：浅色顶栏 + 深色表。P4 之前外观卡不上生产。  
- **`/透明度` 直接套变量**：按钮 hover 失效或颜色不对。  
- **帮助站 / 助理落在最后**：用户觉得没改完。  
- **规范未改就开工**：PR 会被现网 front-end 规则打回。  
- **登出误清主题**：清 `brabus_user` 时不得碰 `brabus_theme`。  
- **漏页**：只改了核价列表，上传/帮助/助理仍深色。P4 用 §3.1 当检查单。  
- **漏加 `?v=`**：浏览器继续用旧 hex 模板。  

---

## 7. 顺序（一览）

```
P0  规范 + theme-tokens.css + theme.js + 防闪
P1  壳层 + 登录 + 个人资料外观卡 + 零件价格一览     ← 试点出口
P2  §3.1 其余全部列表（含一事一议、溯源、用户、日志）
P3  §3.1 全部上传/计算/仪表盘/结构/图/引擎/系统设置
    + AI 助理 + 帮助站 5 页
P4  §3.1 逐行 × 深/浅打勾 → 合入生产（用户才看见外观卡）
```

**以上计划不执行。** 2026-08-28 决定维持深色，不改代码。
