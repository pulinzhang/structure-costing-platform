# 浅色主题改造 — 设计说明

> 状态：**设计定稿（待开发）**  
> 关联：`.cursor/rules/front-end.mdc`、`docs/front-end.mdc`、`static/css/style.css`、`static/index.html`、`static/login.html`、`static/js/features/**`  
> 原则：**深色与浅色同时存在，本机 `localStorage` 记忆，不进账号、不进后端。** 禁止「只改 `:root`」或「每个 class 写两套 hex」。必须先收成语义色 token；浅色 HUD 去掉霓虹 glow。

---

## 0. 一句话

> **把写死的 Brabus hex 收成一套 CSS 语义变量；深色 / 浅色两套色板挂在 `html[data-theme]` 上；用户在个人资料页切换，写入本机 `localStorage`（`brabus_theme`），刷新、关浏览器、登出后再进仍是上次选的。**

不是换掉暗色。不是跟账号走。不是全站反相。后端不动。

---

## 1. 为什么要改

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
| G3 | 颜色进入语义 token（`--bg-canvas` / `--text-muted` 等），模板不再写业务 hex |
| G4 | 浅色 HUD：**实心红 + 淡红底 KPI 列**，去掉 `text-shadow` / 霓虹 glow / 大块黑阴影；深色 HUD 可保留现网发光 |
| G5 | 登录、主应用、Toast、侧栏、顶栏、抽屉、AI 助理、帮助站读**同一** `brabus_theme` |
| G6 | 选择只存在本机 `localStorage`，不进用户表、不进 API |
| G7 | 落地时同步改 `docs/front-end.mdc` 与 `.cursor/rules/front-end.mdc`（两处一起改） |

后端、权限码、Hash 路由、API 契约 **不在目标内**。

---

## 3. 范围边界

### 3.1 做

- `static/css/style.css` 壳层（侧栏 Overlay、顶栏、滚动条、autofill、selection）
- `static/index.html` / `static/login.html` 入口 class
- 全部业务 `template.js` + 行/抽屉 HTML 所在的 `index.js`
- `static/js/main.js`（Toast 等全局 UI）
- `static/js/page-size.js` 分页控件 class
- `static/js/llm-assistant/**` 浮动助理
- `static/helper/**` 帮助站（独立暗色 CSS，需跟主站浅色对齐或提供同一 token）
- 产品结构图（`bom/material/viz`）节点色按浅底重调
- 打印 / 导出相关样式（助理 `export/print.js` 等）若写死暗色则一并收口
- 个人资料页（`#/settings-profile`）「外观」卡片：深 / 浅切换；入口 html 启动时读 `localStorage` 防闪

### 3.2 不做

| 不做 | 说明 |
|------|------|
| 后端 / 数据库 / API | 主题是纯前端 |
| 权限、路由名、侧栏信息架构 | 只换皮 |
| 为主题引入构建链 / 换 UI 框架 | 继续 Tailwind CDN + 原生 JS |
| 历史页「看起来差不多就行」的半吊子 | 要么全站 token 化，要么先试点再全量；禁止长期两套皮肤混用 |
| 浅色上保留暗色霓虹 HUD | 见 §5.3；深色可以留 |
| 主题跟账号 / 服务端配置 | 只认本机 `localStorage`，登出不清主题 |
| 顶栏 / 登录页放主题开关 | 入口只在个人资料；顶栏保持现网信息密度 |
| 主题写入 `PUT /api/auth/me` | 本机记忆，不进用户资料接口 |
| 跟随系统 `prefers-color-scheme` | 不做自动跟随，避免和本机记忆打架 |

### 3.3 已拍板 / 仍待拍板

| # | 问题 | 结论 |
|---|------|------|
| D1 | 深色与浅色？存在哪里？ | **已拍板：两套都在。本机 `localStorage`，键 `brabus_theme`。** 详见 §5.2 |
| D2 | 浅色 HUD 是否去掉霓虹发光？ | **去掉**。浅底用实心红 + 淡红底；深色保持现网 HUD |
| D3 | 先试点还是一次全量？ | **先试点**：壳层 + 个人资料外观卡 + 零件价格一览，两套主题都过，再全量 |

工期按双主题计：约 **5–7 周**（1 人全职，含深/浅各验一遍）。

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
| `--bg-surface` | `#FFFFFF` | 卡片 / 表外框 / 抽屉面板 |
| `--bg-elevated` | `#FAFAFA` | 输入、表头条、次级槽 |
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
| `--bg-surface` | `#0A0A0C` / `#1e1e1e` | HUD 外框 / 面板（落地时表外框与普通面板可拆 `--bg-table` 若一值不够） |
| `--bg-elevated` | `#0a0a0a` / `#262626` | 输入 / 抬升 |
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

若表外框 `#0A0A0C` 与卡片 `#1e1e1e` 不能共用一个 `--bg-surface`，允许加 `--bg-table`，两套主题都要赋值。不要为每个页面加私有色。

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
| Toast | `#1e1e1e` + 重阴影 | `--bg-surface` + 细边 + 轻阴影 |
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
- 新增：允许并要求 `html[data-theme="light"|"dark"]`；禁止再写死 `bg-[#0a0a0a]` 当画布。

`docs/front-end.mdc` 与 `.cursor/rules/front-end.mdc` 必须同步改。

---

## 5. 技术设计

### 5.1 Token 如何进 Tailwind

无构建，只能让 **class 引用变量**，切换主题时只改变量。

推荐两种等价写法，全站选一种：

```html
<!-- A. 任意值指向变量（改动最小） -->
<div class="bg-[var(--bg-surface)] text-[var(--text-main)] border-[var(--border-color)]">

<!-- B. CDN 配置语义色名（class 更短） -->
<script>
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          canvas: 'var(--bg-canvas)',
          surface: 'var(--bg-surface)',
          /* …与 §4.1 对齐… */
        }
      }
    }
  }
</script>
<div class="bg-surface text-main border-color">
```

**禁止**继续写 `bg-[#0a0a0a]` 作为业务底色。例外：品牌红若已是 token，不要再写死 `#d32f2f`；红底按钮上的 `text-white` **允许**（对比度需要）。

壳层 CSS（`.sidebar`、`.page-header` 等）去掉写死的 `#121214`、`rgba(255,255,255,0.08)`，全部改为 `var(--…)`。需要新增的壳层专用 token（侧栏字色透明度、遮罩）可以加，但不要为单个业务页加 class。

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

#### 切换（入口只在个人资料）

- **唯一操作入口**：`#/settings-profile` 个人资料页。现网该页是「身份摘要 + 基本资料 + 安全设置」；新增独立卡片 **「外观」**，不要塞进「基本资料」表单（那张卡要点保存才生效，主题必须立刻换）。
- 建议位置：三列网格下方通栏卡片（与改密物理隔离）；卡片内两项：**深色 / 浅色** 分段选择（或 radio），当前项高亮品牌红。不要只放无文字的月亮图标。
- **立刻生效**：点选即 `applyTheme(...)`，**没有「保存」按钮**，不调 `PUT /api/auth/me`。
- 权限：能打开个人资料页即可改主题（`menu:settings-profile` / `canAccessPage`）。**不要**挂在 `op:settings-profile:update` 上——那是改姓名邮箱；无更新权限的人仍应能选深浅。
- **顶栏、登录页、帮助站都不放开关。** 它们只在加载时读 `brabus_theme` 上色。未登录用户看到的是这台机器上次选的（默认深色）。
- 行为：`setAttribute('data-theme', …)` + `localStorage.setItem('brabus_theme', …)`。隐私模式写入失败时仍切换当次会话，Toast「无法记住主题」。
- 实现：一个小模块（如 `static/js/theme.js`），`applyTheme(next)` / `getTheme()`。禁止各页自己读写键。个人资料 `index.js` 只调这个模块。
- 帮助站与登录页加载同一套**读取**逻辑（防闪脚本即可），避免主站浅色、帮助仍深色。

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

按类型扫，不要按「看起来像的 hex」全局替换：

1. **壳层**：`style.css`、`index.html` 顶栏/侧栏上的少量 hex  
2. **全局 JS**：`main.js` Toast、`page-size.js`  
3. **登录**  
4. **标准 HUD 列表**（先改标杆 `costing/stamping-part-cost/list`，再复制模式到加工费 / 钢材 / 焊接费等同构页）  
5. **计算 / 上传页**（表单密度低于 HUD，但 hex 同样写死）  
6. **设置 / 用户 / 日志**（规范允许略大字号，仍走同一 token）  
7. **特殊**：仪表盘、结构图、核价引擎、AI 助理、帮助站  

同一语义在 `template.js` 与 `index.js` 行渲染必须一起改，否则表头浅、行仍暗。

### 5.5 验收（前端目视，无单测要求）

每个已改页面至少走：

- 列表有数据 / 空状态 / 加载  
- 筛选、分页、每页条数  
- 操作列打开抽屉（不是整行点击）  
- 主按钮 / 次按钮 / 危险按钮 hover  
- 登录成功与失败 Toast  
- 桌面宽度；侧栏 Overlay 开合  

试点通过后再铺全站。全量完成后按 `features/index.js` 的 `pageMeta` 路由清单一页不漏。**每个页面深色、浅色各点一遍**；刷新后主题仍在；登出再登录主题仍在。

---

## 6. 工作量

按 **1 名熟悉本仓库前端的人全职** 估，含深/浅两套目视验收。D3 试点约 **4–6 人天**（含开关与防闪）。

本期就是双主题，不再分「先只上浅色」。

| 块 | 内容 | 人天 |
|----|------|------|
| 规范 + 两套色板 | 改两份 `front-end.mdc`、token 对照 | 1–2 |
| 主题模块 | `brabus_theme`、防闪脚本、个人资料「外观」卡 | 1 |
| 壳层 | `style.css` 全部改 token；深/浅侧栏与顶栏 | 2 |
| 登录 | 模板 + 与主站同一记忆 | 0.5 |
| Token 替换 | ~40 个 template + 行渲染 index + 分页 + Toast | 5–7 |
| HUD | 浅色去 glow；深色对齐现网 | 3–4 |
| 特殊页 | 仪表盘、结构图（切换要重绘）、引擎、设置 | 2.5 |
| 周边 | LLM 助理、帮助站、打印 | 1.5 |
| 验收 | 40+ 路由 × 深/浅 × 列表/空/错/抽屉；刷新/登出记忆 | 5–7 |
| **合计** | | **约 22–28 人天（5–7 周）** |

### 6.1 风险

- **语义误分类**：同一 `#555555` 不能当成一个 token 全局替换。  
- **漏改 `index.js`**：模板浅了、行渲染仍黑。  
- **帮助站 / 助理落在主站后面**：用户会觉得「没改完」。  
- **规范未改就开工**：后续 PR 会被现网 front-end 规则打回浅色 class。
- **键名写错 / 多处各读各的**：登录与主站主题不一致。只允许一个模块碰 `brabus_theme`。
- **权限绑错**：用 `op:settings-profile:update` 藏外观卡，导致只能改资料的人才能换主题。入口跟菜单走即可。
- **登出误清主题**：`brabus_user` 清除时不得 `removeItem('brabus_theme')`。

---

## 7. 建议落地顺序

```
改设计规范（两份 front-end.mdc）
    → 主题模块 + 防闪 + 个人资料「外观」卡（localStorage）
    → 试点：壳层 + 个人资料 + 零件价格一览（深/浅都过）
    → 按 §5.4 铺全站
    → 全路由 × 两套主题验收（含刷新、登出后再进）
```

D1 已拍板。未开工前本文继续只改设计、不改业务代码。
