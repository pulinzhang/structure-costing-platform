# 浅色主题改造 — 设计说明

> 状态：**设计定稿（待拍板 / 待开发）**  
> 关联：`.cursor/rules/front-end.mdc`、`docs/front-end.mdc`、`static/css/style.css`、`static/index.html`、`static/js/features/**`  
> 原则：**只改前端观感，不改后端 / API / 权限 / 路由。** 禁止「只改 `:root` 变量」或「每个 class 写两套 hex」。必须先收成语义色 token，再换浅色色板。HUD 浅色上去掉霓虹 glow。

---

## 0. 一句话

> **把写死在 Tailwind hex 里的 Brabus 暗色，收成一套 CSS 语义变量；浅色作为办公默认皮肤，工业红与密表结构保留，霓虹发光不带到浅底上。**

不是换一套 Material / Ant Design。不是全站反相（黑变白）。后端不动。

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
| G1 | 办公场景下一套可读的浅色皮肤：画布灰白、面板白、灰边、深字 |
| G2 | 品牌红仍是唯一强调色；表体直角、密表、等宽数字、操作只走操作列 |
| G3 | 颜色进入语义 token（`--bg-canvas` / `--text-muted` 等），模板不再写业务 hex |
| G4 | 浅色 HUD：**实心红 + 淡红底 KPI 列**，去掉 `text-shadow` / 霓虹 glow / 大块黑阴影 |
| G5 | 登录、Toast、侧栏、顶栏、抽屉、空状态、滚动条、autofill 与业务页同一套色 |
| G6 | 落地时同步改 `docs/front-end.mdc` 与 `.cursor/rules/front-end.mdc`（两处一起改） |

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

### 3.2 不做

| 不做 | 说明 |
|------|------|
| 后端 / 数据库 / API | 主题是纯前端 |
| 权限、路由名、侧栏信息架构 | 只换皮 |
| 为主题引入构建链 / 换 UI 框架 | 继续 Tailwind CDN + 原生 JS |
| 历史页「看起来差不多就行」的半吊子 | 要么全站 token 化，要么先试点再全量；禁止长期两套皮肤混用 |
| 浅色上保留暗色霓虹 HUD | 见 §5.3 |

### 3.3 待拍板（建议默认）

落地前请书面确认下面三项。文档按「建议默认」写后续章节；若拍板不同，先改本文再开发。

| # | 问题 | 建议默认 |
|---|------|----------|
| D1 | 全员浅色，还是暗/浅可切换？ | **浅色默认**；架构按可切换预留 token（`html[data-theme]`）。开关 UI 可二期 |
| D2 | 浅色 HUD 是否去掉霓虹发光？ | **去掉**。浅底用实心红 + 淡红底 |
| D3 | 先试点还是一次全量？ | **先试点**：壳层 + 登录 + 零件价格一览（现网 HUD 标杆），视觉过了再全量 |

工期随 D1 变化：仅浅色约 3–4 周；带切换约 5–7 周（1 人全职，含全路由目视验收）。

---

## 4. 设计语言：Brabus Precision Light

暗色理念保留三句话：**极简克制、工业精密、红色唯一强调**。换掉的是「碳素黑底 + 发光」。

### 4.1 色板（浅色默认）

落地时写入 `:root`（或 `html[data-theme="light"]`）。名称用语义，不要用 `gray-500` 这种与 Tailwind 默认冲突的名字。

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

暗色若二期保留，作为 `html[data-theme="dark"]` 覆盖同一批 token，映射回现网阶梯（`--bg-canvas: #0a0a0a` 等）。本文不展开暗色色板——现网即暗色真相。

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
- 浅色页内强调红只许 `--brabus-red`（`#d32f2f`）。

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

### 5.2 主题挂载（即使第一期不上开关）

```html
<html lang="zh-CN" data-theme="light">
```

- 第一期：写死 `light`，或启动时读 `localStorage`（若已有值）否则 `light`。
- 第二期：顶栏增加切换，写入 `localStorage`，改 `document.documentElement.dataset.theme`。
- 防闪：`index.html` / `login.html` 在 Tailwind 之前用极短内联脚本设 `data-theme`，避免先暗后浅。

`body` 不要再写 `bg-[#0a0a0a]`，改为 `bg-[var(--bg-canvas)]` 或等价语义 class。

### 5.3 不能只换 token 的部分（必须重画）

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

试点通过后再铺全站。全量完成后按 `features/index.js` 的 `pageMeta` 路由清单一页不漏。

---

## 6. 工作量

按 **1 名熟悉本仓库前端的人全职** 估，含目视验收。D3 试点约 **3–5 人天**，可从全量表中单列。

### 6.1 方案 A：全站浅色（无切换 UI）

| 块 | 内容 | 人天 |
|----|------|------|
| 规范 + 色板 | 改两份 `front-end.mdc`、token 表、试点对照 | 1–2 |
| 壳层 | `style.css`、入口 html | 1.5 |
| 登录 | 登录页模板 | 0.5 |
| Token 替换 | ~40 个 template + 行渲染 index + 分页 + Toast | 5–7 |
| HUD 重画 | 十来个密表：去 glow、KPI 列、筛选条 | 3–4 |
| 特殊页 | 仪表盘、结构图、引擎、设置 | 2 |
| 周边 | LLM 助理、帮助站、打印 | 1.5 |
| 验收 | 40+ 路由 × 列表/空/错/抽屉 | 3–5 |
| **合计** | | **约 18–24 人天（3–4 周）** |

### 6.2 方案 B：暗/浅可切换

方案 A 全部 + 顶栏开关、`localStorage`、防闪、**两套色板各验一遍** → 再 **+8–12 人天（合计 5–7 周）**。

架构上方案 A 若已按 `data-theme` + token 落地，方案 B 的增量主要是开关与暗色验收，而不是再扫一遍 hex。

### 6.3 风险

- **语义误分类**：同一 `#555555` 不能当成一个 token 全局替换。  
- **漏改 `index.js`**：模板浅了、行渲染仍黑。  
- **帮助站 / 助理落在主站后面**：用户会觉得「没改完」。  
- **规范未改就开工**：后续 PR 会被现网 front-end 规则打回浅色 class。

---

## 7. 建议落地顺序

```
拍板 D1 / D2 / D3
    → 改设计规范（两份 front-end.mdc）
    → 试点：壳层 + 登录 + 零件价格一览
    → 目视过审
    → 按 §5.4 铺全站
    → 全路由验收
    →（可选二期）主题开关
```

未拍板前 **不改业务代码**。本文只定设计与路径。
