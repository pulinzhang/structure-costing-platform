# 用户权限树设计说明

> 状态：已落地  
> 范围：菜单可见性 + 功能按钮可见性 + 后端 API 鉴权（**前后端同码双向判断**）  
> 关联：  
> - 目录源 `app/common/permissions/catalog.json`  
> - 常量 `app/common/permissions/codes.py`（`Perm.*`）  
> - 路由依赖 `app/deps/permissions.py`  
> - 前端 `static/js/permissions.js`（`can` / `canAccessPage` / `applySidebarPermissions`）  
> - API 类型安全层只留短约束：`docs/api-type-safety.md` §7.0、`.cursor/rules/api-type-safety.mdc` §7.0（**权限细则以本文为准**）  

---

## 0. 新增功能标准流程（必读）

新增页面 / 按钮 / API 时，**同一权限码**必须在前后端同时落地。缺一侧 = 未完成。

### 0.1 改什么（清单）

| # | 层 | 动作 | 文件 / 位置 |
|---|---|---|---|
| 1 | 目录 | 在树中增加 `menu:*` / `op:*`（及分组） | `app/common/permissions/catalog.json` |
| 2 | 常量 | 重新生成 `Perm.*` | `python -X utf8 scripts/generate_perm_codes.py` → `codes.py` |
| 3 | 后端路由 | 每个业务端点挂权限依赖 | `Depends(require_perm(Perm.XXX))` 等 |
| 4 | 后端写操作 | Service 收 `current_user=`；**默认不再二次 `require_permission`**（见 §0.2 例外） | 对应 `*_service.py` |
| 5 | 前端菜单 | 侧栏增加 `data-page="{page-key}"`；page-key 默认对应 `menu:{page-key}`（系统设置页例外见 §4.1） | `static/index.html` |
| 6 | 前端路由 | `app.js` 的 `pages` 注册新 page；`canAccessPage` 自动拦无权限直链 | `static/js/app.js` |
| 7 | 前端按钮 | 同 `op` 码：`can('op:…')` 或模板条件渲染 | 对应 `features/**/index.js`、`template.js` |
| 8 | 授权 | admin 在用户授权树勾选后，目标用户重新登录或 `me`/`touch` 刷新会话 | 用户管理「授权」 |
| 9 | 文档 | 若树结构有评审需要，同步更新本文 §7 可读清单 | `docs/permission-design.md` |

### 0.2 后端写法（强制）

```python
from app.common.permissions.codes import Perm
from app.deps.permissions import require_perm, require_any_perm, require_admin_user

# 读
current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW))

# 写（再传 Service）
current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_DELETE))

# 共享接口（任一即可）
current_user: UserVO = Depends(
    require_any_perm(Perm.STAMPING_PARTS_VIEW, Perm.STEEL_PRICE_CALC_VIEW)
)

# 仅管理员（权限树 / 写授权）
current_user: UserVO = Depends(require_admin_user)
```

**禁止**：业务路由裸 `Depends(get_current_user)`；禁止 `require_perm("op:…")` 字面量。  
**例外**：仅 `login` 无用户；`me` / `touch` / `logout` 可用 `get_current_user`。

**Service 层权限再校验（例外，勿扩散）**：

| 模块 | 行为 |
|---|---|
| 默认业务 Service | **只信 Router 已注入的权限**；不再调用 `require_permission` |
| `UserService` 写操作 | Router 已挂 `Perm.SETTINGS_*`，Service 内再 `require_permission` 一次（用户管理敏感操作双保险） |
| `PermissionService` | Router 已 `require_admin_user`，Service 内再 `require_admin` |

新增业务模块不要复制「双检」；统一在 Router 用 `require_perm` 拦截即可。

### 0.3 前端写法（强制）

```javascript
import { can, canAccessPage } from '../../../permissions.js?v=…';

// 菜单：侧栏 a[data-page="my-page"] → 默认校验 menu:my-page
// 路由：app.js 已用 canAccessPage(page) 拦截，无权限跳 fallbackPageName()

// 按钮：与后端同一 op 码
if (!can('op:my-page:create')) { /* 隐藏或禁用 */ }
// 或模板：${can('op:my-page:export') ? `<button…>` : ''}
```

会话字段（登录 / `me` / `touch`）：`is_admin`、`permissions[]`。  
`can(code) = is_admin || permissions.includes('*') || permissions.includes(code)`。

### 0.4 双向对照（同一功能）

| 能力 | 前端判断 | 后端判断 |
|---|---|---|
| 进入页面 | `canAccessPage('stamping-parts')` → `menu:stamping-parts` | 该页所有读 API → `Perm.STAMPING_PARTS_VIEW` |
| 显示「删除」按钮 | `can('op:stamping-parts:delete')` | `DELETE` → `Perm.STAMPING_PARTS_DELETE` |
| 显示「上传」 | `can('op:stamping-upload:upload')` | `POST` 上传 → `Perm.STAMPING_UPLOAD_UPLOAD` |
| 授权抽屉 | 仅 `is_admin` 见按钮 | `require_admin_user` |

**原则：前端藏 UI = 体验；后端 403 = 安全。只做前端不算完成。**

### 0.5 自检

- [ ] `catalog.json` 有新 code；跑过 `generate_perm_codes.py`；启动无「权限码不同步」
- [ ] 每个新/改 API 均有 `require_perm(Perm.…)`（或 any / admin）
- [ ] 每个新按钮 / 菜单有对应 `can` / `data-page`
- [ ] 非授权用户：侧栏无入口、直链被拦、按钮不可见、curl API 返回 403
- [ ] `is_admin`：前后端全放行

---

## 1. 目标

在登录体系之上，提供一套简单的**用户级权限树**：

1. 权限按「根 → 菜单/分组 → 操作」组织。
2. 管理员在用户列表点击「授权」，弹出可勾选的展开树。
3. 无菜单权限 → 侧边栏不显示，Hash 路由不可进入。
4. 无操作权限 → 对应按钮不显示，相关 API 返回 403。
5. **仅 `is_admin` 可授权**；前端隐藏不够，后端必须校验。

管理员判定用 `users.is_admin`，禁止 `username == "admin"`。

---

## 2. 已确认规则

| # | 议题 | 结论 |
|---|---|---|
| 1 | 新建用户默认权限 | **仪表盘 + 个人资料**（见 §6） |
| 2 | 分组节点（冲压工程、一事一议等） | **可勾选**，授权更直观 |
| 3 | 个人资料 | **强制权限，人人必有，授权时不可取消** |
| 4 | 谁能授权 | 仅 `is_admin == true` |
| 5 | 角色模板 | 本期不做；用户直接勾选权限码 |
| 6 | 权限目录存放 | **后端固定 `catalog.json`**（不进业务表、不做菜单 CMS） |

---

## 3. 核心原则

1. **前端藏 UI = 体验；后端鉴权 = 安全。** 只藏菜单/按钮不够。
2. **权限码是唯一真相**；树只是展示形态。
3. **`is_admin` 特权通道**：拥有全部权限，跳过码表校验；与权限码正交（不要用「授权树勾选」变成管理员）。
4. **权限目录 = 仓库内固定 JSON**（`catalog.json`）：与代码一起发版；新增功能主要维护该文件。不把目录放进业务表，也不做后台可编辑菜单。
5. **用户权限扁平存储**：`user_permissions` 只存已勾中的 `permission_code`（「某人勾了什么」才进库）。

---

## 4. 权限码命名

| 类型 | 格式 | 作用 |
|---|---|---|
| 分组 / 菜单 | `menu:{key}` | 控制侧栏显示；分组也可勾 |
| 操作 | `op:{page-key}:{action}` | 控制按钮 + API |

### 4.1 命名冲突处理

侧栏「设置」既是分组又有「系统设置」叶子页。约定：

| 节点 | code |
|---|---|
| 设置（分组） | `menu:settings` |
| 系统设置（叶子页） | `menu:settings-system` |
| 个人资料 | `menu:settings-profile` |
| 用户管理 | `menu:settings-users` |
| 操作日志 | `menu:settings-logs` |

叶子页的 `data-page` / 路由 key 仍可为 `settings`；权限码用 `settings-system` 避免与分组撞名。实现时在「路由 page → menu code」映射表中写死即可。

同理：产品结构路由 page 为 `bom-structure`（`#/bom-structure`），与权限码 `menu:bom-structure` 一致。
旧临时路由 `#/bom-list` 会重定向到 `bom-structure`。

---

## 5. 数据模型

### 5.1 `users` 表增量

```text
is_admin  BOOLEAN  NOT NULL  DEFAULT 0
```

- 启动种子账号 `admin`：`is_admin = true`。
- 判定管理员用 `is_admin`，禁止 `username == "admin"`。
- 系统至少保留 1 个 `is_admin`；禁止通过业务操作去掉最后一个管理员。

### 5.2 `user_permissions` 表

```text
user_permissions
  id                  INTEGER PK
  user_id             INTEGER FK → users.id  (级联删除)
  permission_code     VARCHAR  NOT NULL
  UNIQUE(user_id, permission_code)
  INDEX(user_id)
```

- 授权保存：**整表覆盖**（事务内按 user_id 删除再批量插入）。
- `is_admin` 用户可不依赖本表（读权限时直接视为全量）。

### 5.3 权限目录：`catalog.json`（已拍板）

**职责划分：**

| 存什么 | 存哪里 |
|---|---|
| 有哪些可勾节点（树、文案、默认/强制） | `app/common/permissions/catalog.json` |
| 某个用户勾了哪些 code | 表 `user_permissions` |
| 是否超级管理员 | 表 `users.is_admin` |

**文件与加载：**

```text
app/common/permissions/
  catalog.json    # 唯一目录源（树 + defaults + mandatory）
  catalog.py      # 启动加载、内存缓存、与 codes.Perm 双向校验
  codes.py        # Perm.* 常量（路由/Service 禁止散落字面量）
  checks.py       # require_admin / require_permission / has_permission
app/deps/permissions.py   # require_perm(Perm.XXX) / require_any_perm / require_admin_user
scripts/generate_perm_codes.py  # 从 catalog.json 重新生成 codes.py
```

- 进程启动（或首次访问）时读入 JSON 并缓存；热改文件需重启进程才生效（可接受，跟发版走）。
- 加载时断言 `codes.Perm` ⊆ / ⊇ catalog 全量 code，不一致则启动失败。
- 路由写 `Depends(require_perm(Perm.DASHBOARD_VIEW))`，不写 `"op:dashboard:view"`。
- `GET /api/permissions/tree` 返回该树（可附带 `mandatory` 标记），前端授权抽屉不另维护一份树。
- 保存用户权限时：提交的 code 必须 ∈ JSON 派生的全量集合；非法 code 拒绝或丢弃。
- **不做**权限节点业务表；将来若真要在线改菜单，再把 JSON 当种子导入表即可。
- 新增权限：先改 `catalog.json`，再跑 `python -X utf8 scripts/generate_perm_codes.py`，路由引用新 `Perm.*`。

**JSON 结构约定：**

```json
{
  "version": 1,
  "defaults": [
    "menu:dashboard",
    "op:dashboard:view",
    "menu:settings",
    "menu:settings-profile",
    "op:settings-profile:view",
    "op:settings-profile:update",
    "op:settings-profile:password"
  ],
  "mandatory": [
    "menu:settings",
    "menu:settings-profile",
    "op:settings-profile:view",
    "op:settings-profile:update",
    "op:settings-profile:password"
  ],
  "tree": [
    {
      "code": "menu:dashboard",
      "label": "仪表盘",
      "type": "menu",
      "children": [
        { "code": "op:dashboard:view", "label": "查看", "type": "op" }
      ]
    },
    {
      "code": "menu:stamping",
      "label": "冲压工程",
      "type": "group",
      "children": []
    }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `type` | `group` 分组 / `menu` 叶子菜单 / `op` 操作 |
| `code` | 稳定权限码，全局唯一 |
| `label` | 授权树展示文案 |
| `children` | 子节点数组；叶子可省略或 `[]` |
| `defaults` | 新建用户写入的 code 列表 |
| `mandatory` | 强制权限；保存时合并；抽屉不可取消 |

节点上也可加 `"mandatory": true` 方便前端灰显；以根级 `mandatory` 数组为准做后端硬约束。

**扩展新功能**：一律走本文 **§0 新增功能标准流程**（改 catalog → 生成 Perm → 后端 `require_perm` → 前端 `can` / 菜单）。不要只改一侧。

---

## 5.4 明确不采用

- 权限/菜单业务表 + 种子数据（本期多余）。
- 纯 Python 大树常量（不如 JSON 好扫、好看）。
- 运行时写文件改 `catalog.json`（目录跟发版走，不跟运营配置走）。

---

## 6. 默认权限与强制权限

### 6.1 新建用户默认写入

```text
menu:dashboard
op:dashboard:view
menu:settings
menu:settings-profile
op:settings-profile:view
op:settings-profile:update
op:settings-profile:password
```

共 7 条。仪表盘默认可在后续授权中取消；个人资料不可取消。

### 6.2 强制权限（不可剥夺）

以下 code **每个用户必须拥有**（含新建、授权保存、历史数据修复）：

```text
menu:settings
menu:settings-profile
op:settings-profile:view
op:settings-profile:update
op:settings-profile:password
```

**实现约束：**

| 层 | 行为 |
|---|---|
| 授权抽屉 UI | 上述节点默认勾选且禁用取消（可标注「必选」） |
| `PUT` 授权接口 | 合并时强制并入 `catalog.json` 的 `mandatory`；即使前端漏传也补回 |
| 创建用户 | Service 写入 `catalog.json` 的 `defaults`（已含强制项） |

父级 `menu:settings` 因强制子项存在，侧栏「设置」分组对任何登录用户至少能打开并看到「个人资料」。

---

## 7. 完整权限树

> 实现时以 `catalog.json` 的 `tree` 为准；下文为与 JSON 对齐的可读清单（新增功能时改 JSON，并同步更新本节便于评审）。

```text
root
│
├── menu:dashboard
│   └── op:dashboard:view
│
├── menu:stamping                              # 冲压工程（分组，可勾）
│   ├── menu:stamping-process                  # 冲压工艺（二级分组，可勾）
│   │   ├── menu:stamping-upload
│   │   │   ├── op:stamping-upload:view
│   │   │   └── op:stamping-upload:upload
│   │   └── menu:stamping-parts
│   │       ├── op:stamping-parts:view
│   │       ├── op:stamping-parts:update
│   │       └── op:stamping-parts:delete
│   ├── menu:stamping-stroke-unit-price        # 冲次单价（二级分组，可勾）
│   │   ├── menu:stamping-tonnage-upload
│   │   │   ├── op:stamping-tonnage-upload:view
│   │   │   └── op:stamping-tonnage-upload:upload
│   │   └── menu:stamping-tonnage
│   │       ├── op:stamping-tonnage:view
│   │       ├── op:stamping-tonnage:create
│   │       ├── op:stamping-tonnage:update
│   │       ├── op:stamping-tonnage:delete
│   │       ├── op:stamping-tonnage:copy
│   │       └── op:stamping-tonnage:export
│   └── menu:stamping-processing-fee           # 冲压加工费（二级分组，可勾）
│       ├── menu:stamping-process-fee-calc
│       │   ├── op:stamping-process-fee-calc:view
│       │   ├── op:stamping-process-fee-calc:run
│       │   └── op:stamping-process-fee-calc:delete
│       └── menu:stamping-process-fee
│           ├── op:stamping-process-fee:view
│           ├── op:stamping-process-fee:update
│           ├── op:stamping-process-fee:delete
│           ├── op:stamping-process-fee:approve
│           ├── op:stamping-process-fee:reverse
│           └── op:stamping-process-fee:export
│
├── menu:yishiyiyi                             # 一事一议（分组，可勾）
│   ├── menu:thickness                         # 加减价政策（二级分组，可勾）
│   │   ├── menu:steel-price-policy-upload
│   │   │   ├── op:steel-price-policy-upload:view
│   │   │   └── op:steel-price-policy-upload:upload
│   │   └── menu:steel-price-policy-download
│   │       ├── op:steel-price-policy-download:view
│   │       ├── op:steel-price-policy-download:export
│   │       └── op:steel-price-policy-download:delete
│   ├── menu:base-price                        # 基准价格（二级分组，可勾）
│   │   ├── menu:base-price-upload
│   │   │   ├── op:base-price-upload:view
│   │   │   └── op:base-price-upload:upload
│   │   └── menu:base-price-download
│   │       ├── op:base-price-download:view
│   │       ├── op:base-price-download:export
│   │       └── op:base-price-download:delete
│   ├── menu:winning-thickness-download        # 中标钢厂厚度价格一览表
│   │   ├── op:winning-thickness-download:view
│   │   └── op:winning-thickness-download:export
│   └── menu:scrap-price                       # 废料月度销售价
│       ├── op:scrap-price:view
│       ├── op:scrap-price:create
│       ├── op:scrap-price:update
│       ├── op:scrap-price:delete
│       ├── op:scrap-price:copy
│       └── op:scrap-price:export
│
├── menu:bom                                   # BOM（分组，可勾）
│   ├── menu:bom-structure                     # 产品结构（路由 page=bom-structure）
│   │   └── op:bom-structure:view
│   └── menu:bom-upload
│       ├── op:bom-upload:view
│       └── op:bom-upload:upload
│
├── menu:costing                               # 核价（分组，可勾）
│   ├── menu:steel-price                       # 冲压钢材联动价（核价第一步）
│   │   ├── menu:steel-price-calc
│   │   │   ├── op:steel-price-calc:view
│   │   │   ├── op:steel-price-calc:run
│   │   │   └── op:steel-price-calc:delete
│   │   └── menu:steel-price-list
│   │       ├── op:steel-price-list:view
│   │       ├── op:steel-price-list:update
│   │       ├── op:steel-price-list:delete
│   │       ├── op:steel-price-list:approve
│   │       ├── op:steel-price-list:reject
│   │       ├── op:steel-price-list:reverse
│   │       └── op:steel-price-list:export
│   └── menu:costing-engine                    # 自动核价引擎（路由 page=costing）
│       └── op:costing:view
│
├── menu:quotation
│   └── op:quotation:view                      # 功能开发中，预留
│
└── menu:settings                              # 设置（分组，可勾；强制保留）
    ├── menu:settings-profile                  # 强制
    │   ├── op:settings-profile:view           # 强制
    │   ├── op:settings-profile:update         # 强制
    │   └── op:settings-profile:password       # 强制
    ├── menu:settings-system
    │   ├── op:settings-system:view
    │   └── op:settings-system:update
    ├── menu:settings-users
    │   ├── op:settings-users:view
    │   ├── op:settings-users:create
    │   ├── op:settings-users:update
    │   ├── op:settings-users:password
    │   ├── op:settings-users:delete
    │   └── op:settings-users:grant            # 授权；实际仅 is_admin 可执行
    └── menu:settings-logs
        ├── op:settings-logs:view
        └── op:settings-logs:export
```

### 7.1 数量汇总

| 类别 | 数量 |
|---|---|
| 分组 `type=group` | 11（`stamping` / `stamping-process` / `stamping-stroke-unit-price` / `stamping-processing-fee` / `yishiyiyi` / `thickness` / `base-price` / `bom` / `costing` / `steel-price` / `settings`） |
| 叶子 `type=menu` | 23 |
| 操作 `op` | 69 |
| 可勾节点合计 | 103（`root` 一般不入库） |
| 新建默认 | 7 |
| 强制 | 5（均包含在默认集内） |

---

## 8. 操作码与 UI 对照

| 页面 key | 操作 code | 对应 UI / 行为 |
|---|---|---|
| dashboard | `view` | 查看 KPI / 统计 |
| stamping-upload | `view` / `upload` | 进入页；「上传」 |
| stamping-parts | `view` / `update` / `delete` | 查询详情；保存工序；删除零件 |
| stamping-tonnage-upload | `view` / `upload` | 查看上传页；导入冲次单价 Excel |
| stamping-tonnage | `view` / `create` / `update` / `delete` / `copy` / `export` | 查询；新增；编辑；删除；复制年度模板；导出 Excel |
| stamping-process-fee-calc | `view` / `run` / `delete` | 查看；执行计算；删除计算日志 |
| stamping-process-fee | `view` / `update` / `delete` / `approve` / `reverse` / `export` | 查询；手工调整；批量删除；审核；反审核；导出 |
| scrap-price | `view` / `create` / `update` / `delete` / `copy` / `export` | 查询；整月保存；删除本月；复制月度；导出 Excel |
| steel-price-policy-upload | `view` / `upload` | 进入页；导入政策 |
| steel-price-policy-download | `view` / `export` / `delete` | 预览；导出 Excel；批量删除 |
| base-price-upload | `view` / `upload` | 进入页；导入基准价格 |
| base-price-download | `view` / `export` / `delete` | 预览；导出；批量删除 |
| winning-thickness-download | `view` / `export` | 预览；导出 Excel |
| bom-structure | `view` | 产品结构：基地/项目卡片浏览 |
| bom-viz（权限码同 `menu:bom-structure`） | `view` | Assembly Workspace |
| bom-upload | `view` / `upload` | 进入页；导入材料清单 |
| steel-price-calc | `view` / `run` / `delete` | 历史/过程；开始计算；删除日志 |
| steel-price-list | `view` / `update` / `delete` / `approve` / `reject` / `reverse` / `export` | 查询；编辑；删除（含批量）；通过（含批量）；驳回；反审核（含批量）；导出 |
| costing（菜单码 `menu:costing-engine`） | `view`（`op:costing:view`） | 自动核价引擎 |
| quotation | `view` | 进入占位页 |
| settings-profile | `view` / `update` / `password` | 查看；改资料/头像；改自己密码 |
| settings-system | `view` / `update` | 查看系统设置；保存设置 |
| settings-users | `view` / `create` / `update` / `password` / `delete` / `grant` | 查询；新增；编辑；重置他人密码；删除；授权 |
| settings-logs | `view` / `export` | 查看审计列表；导出 Excel |

批量操作与单条操作共用同一 `op`（例如批量删除与单条删除均校验 `…:delete`）。

---

## 9. 勾选联动（授权树 UI）

| 动作 | 行为 |
|---|---|
| 勾选子菜单 / 操作 | 自动勾选祖先分组与对应叶子菜单 |
| 勾选操作 | 自动勾选所属叶子 `menu:*` + 祖先 |
| 取消分组 | 取消其下全部子菜单与操作（**强制节点除外，保持勾选**） |
| 取消叶子菜单 | 取消其下全部操作（强制菜单不可取消） |
| 只勾分组、不勾子项 | 允许保存；侧栏父级显示规则见 §10（无可见子项则隐藏分组） |
| 父节点快捷操作 | 可选：点击分组一键全选 / 全不选子树（跳过强制节点） |

分组 code 一并入库，便于授权回显；**真正控制页面进入的是叶子 `menu:*`**。

---

## 10. 前后端双向行为（同码）

### 10.1 登录 / `me` / `touch`

响应中的用户对象必须含：

```text
is_admin: bool
permissions: string[]   # is_admin 时可 ["*"] 或全量；前端统一用 can()
```

前端封装（`static/js/permissions.js`）：

```text
PAGE_MENU_CODE = {
  settings: 'menu:settings-system',   # 路由 key 与分组码撞名
  'bom-viz': 'menu:bom-structure',    # Workspace 与产品结构同权
  costing: 'menu:costing-engine',     # 分组为 menu:costing，叶子为引擎
}

can(code) => is_admin || permissions.includes("*") || permissions.includes(code)
menuCodeForPage(page) => PAGE_MENU_CODE[page] || `menu:${page}`
canAccessPage(page) =>
  page === 'costing'
    ? can('menu:costing-engine') || can('menu:costing')   # 兼容旧授权只勾分组
    : can(menuCodeForPage(page))
```

会话（localStorage）同步保存 `is_admin`、`permissions`；授权变更后目标用户需重新登录或下次 `me`/`touch` 刷新。

**授权注意**：`menu:costing` 现为分组；进入自动核价引擎应勾选叶子 `menu:costing-engine`（及 `op:costing:view`）。旧数据仅有 `menu:costing` 时前端仍可进页，但建议补授叶子码。

### 10.2 侧边栏与路由（前端 menu）

| 动作 | 实现 |
|---|---|
| 隐藏无权限菜单 | `applySidebarPermissions()`：按 `a[data-page]` → `canAccessPage` |
| 空分组隐藏 | 无可见子项的 `.has-submenu` 一并 hidden |
| 直链 Hash 无权限 | `app.js` 调 `canAccessPage`；失败则 `fallbackPageName()`（优先仪表盘，否则个人资料）+ Toast |

### 10.3 按钮（前端 op）

各页 `init` / 渲染前：

```text
can('op:{page}:{action}')
```

模板内亦可：`` ${can('op:…') ? `<button…>` : ''} ``。

**禁止**仅靠藏按钮而不挂后端 `require_perm`。

### 10.4 后端 API（op / admin）

| 类型 | 依赖 |
|---|---|
| 业务读 / 写 / 删 / 导出 / 上传 | `require_perm(Perm.…)` |
| 多页共享读接口 | `require_any_perm(Perm.A, Perm.B, …)` |
| 权限树、读写用户授权 | `require_admin_user` |
| `me` / `touch` / `logout` | `get_current_user` |
| `login` | 无 |

失败：`PermissionException` → HTTP **403**。

### 10.5 用户列表「授权」

- 前端：仅 `is_admin`（或兼有 `op:settings-users:grant`）显示「授权」。
- 后端：树 / 读写权限接口一律 `require_admin_user`。
- 保存：覆盖写入并强制合并 `mandatory`。

---

## 11. API 设计

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| `GET` | `/api/permissions/tree` | `require_admin_user` | 返回 catalog 树（含 mandatory 标记） |
| `GET` | `/api/users/{id}/permissions` | `require_admin_user` | 已授权 code 列表 |
| `PUT` | `/api/users/{id}/permissions` | `require_admin_user` | `{ codes: string[] }`，覆盖 + 合并必选码 |
| `GET` | `/api/auth/me` | 登录 | 含 `is_admin`、`permissions` |

用户 CRUD：`op:settings-users:*`（`Perm.SETTINGS_USERS_*`）；授权执行仍以 `is_admin` 为准。

### 11.1 校验辅助

```text
# Router（默认拦截点）
require_perm(Perm.…) / require_any_perm(…) / require_admin_user

# Service（例外，见 §0.2）
require_admin(current_user)                    # PermissionService
require_permission(current_user, Perm.…)       # 仅 UserService 写操作双保险
# is_admin → 放行；否则查 permissions；失败 → PermissionException → 403
```

分层：Router 注入带权限的 `current_user` → Service 业务（用户模块可再校验）→ Repository 只访问数据。

---

## 12. 代码落点

```text
app/common/permissions/
  catalog.json              # 【唯一目录源】
  catalog.py                # 加载缓存 + 与 Perm 双向校验
  codes.py                  # Perm.*（禁止路由字面量）
  checks.py                 # has_permission / require_*
app/deps/permissions.py     # require_perm / require_any_perm / require_admin_user
scripts/generate_perm_codes.py

app/models/user.py          # is_admin
app/models/user_permission.py
app/repositories/user/user_permission_repository.py
app/services/user/permission_service.py
app/routers/user/permissions.py

static/js/permissions.js    # can / canAccessPage / applySidebarPermissions
static/js/app.js            # 侧栏过滤 + 路由守卫
static/js/features/**       # 按钮级 can()
static/index.html           # 侧栏 data-page
```

---

## 13. 实施状态

下列项均已落地；后续只按 **§0** 增量扩展：

1. `catalog.json` + `codes.Perm` 双向校验  
2. `is_admin` + `user_permissions`；bootstrap 管理员 / mandatory  
3. 登录 / `me` 返回权限；前端 `can()`  
4. 用户授权抽屉（强制节点不可取消）  
5. 侧栏 + Hash 路由守卫  
6. 各业务页按钮 `can`  
7. 业务 API 统一 `require_perm(Perm.…)`  

---

## 14. 明确不做（本期）

- 角色表 / 角色模板（如「核价员」「只读」一键套用）——可后续叠加。
- 权限/菜单业务表，或后台可编辑动态菜单。
- 运行时改写 `catalog.json`。
- 数据行级权限（按基地/车型隔离）——另案。
- 用 `username === "admin"` 判断管理员。

---

## 15. 验收清单

- [ ] 新建用户自动拥有仪表盘 + 个人资料权限。
- [ ] 任意授权保存后，个人资料相关 5 个 code 仍在；抽屉无法取消。
- [ ] 非 admin 看不到「授权」；调用授权 API 返回 403。
- [ ] 去掉某菜单权限后，侧栏隐藏且直链 hash 被拦截。
- [ ] 去掉某操作权限后，按钮不显示且对应 API 403。
- [ ] `is_admin` 可见全部菜单与按钮，API 全部放行。
- [ ] 最后一个 admin 不可被降权/删除导致系统无管理员。
- [ ] 新增功能按 §0：catalog / Perm / 后端 require_perm / 前端 can 四处齐全。

---

## 修订记录

| 日期 | 说明 |
|---|---|
| 2026-08-12 | 初稿：权限树、默认/强制规则、完整 code 清单、API 与实施顺序 |
| 2026-08-12 | 拍板：权限目录用后端固定 `catalog.json`；库表只存用户已授权 code |
| 2026-08-12 | 首版落地：catalog、is_admin、user_permissions、授权 API/抽屉、侧栏与路由守卫 |
| 2026-08-12 | 路由统一 `require_perm(Perm.*)`；`codes.py` + 启动双向校验 |
| 2026-08-12 | 增补 §0「新增功能标准流程」；前后端同码双向写入；对齐 api-type-safety §7.0 |
| 2026-08-12 | 减熵：api-type-safety §7.0 收短链；删除未用 hideIfCannot/disableIfCannot；明确 UserService 双检为例外 |
| 2026-08-12 | 新增 `menu:settings-logs` / `op:settings-logs:view|export`；操作日志页与导出审计 |
| 2026-08-13 | 新增 `menu:scrap-price` / `op:scrap-price:view|create|update|delete|copy`；废料月度销售价后端 |
| 2026-08-13 | 废料销售价增加 `op:scrap-price:export` 与宽表 Excel 导出 |
| 2026-08-13 | 冲压工程侧栏拆分：`menu:stamping-process` / `menu:stamping-stroke-unit-price` / `menu:stamping-processing-fee` 二级分组对齐 UI |
