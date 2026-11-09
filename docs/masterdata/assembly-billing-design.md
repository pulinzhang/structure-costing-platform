# 总成分类、费用档案、计费管理 — 设计说明

> 状态：**已落地**  
> 归属：`masterdata`。三张表、三个维护页，侧栏收在同一个二级菜单「总成计费」下。  
> 本期只建档案和对照。不改总成核价、不改包装运输上传、不改系统费率、不给零件或 BOM 打分类。

---

## 0. 一句话

> **主数据里放三张表：总成分类是件的种类，费用档案是费的种类并带一个计费率，计费管理登记「这一类计哪些费」。一个分类对应多条计费，一条计费只指向一个分类、一个费用。选用之后用的就是该费用档案上的那一个率。**

首期分类四行：冲压件、凸焊件、总成件、黑漆件。首期费用六行：仓储+包装、运输、管理费、财务费、报废费用、税前利润。以后加种类是加行，不改表。

---

## 1. 为什么做

核价现在把间接费写死在公式和系统费率里：运输、仓储捆包来自包装档案，管理费、财务费、报废费用、税前利润按成品基数乘统一费率。件本身没有「它属于哪一类、这一类计哪些费」的档案。

要先有三本可维护的主数据，后面核算才知道按类取费。本期停在档案，不把现网 I1～I8 改成读这三张表。

---

## 2. 三张表各管什么

| 表 | 业务名 | 回答的问题 | 关系 |
|----|--------|------------|------|
| `assembly_categories` | 总成分类 | 这是冲压件、凸焊件、总成件还是黑漆件 | 独立主数据 |
| `fee_archives` | 费用档案 | 仓储+包装、运输、管理费、财务费、报废费用、税前利润各是哪一种费，以及它的计费率（2%、0.3% 这类百分数） | 独立主数据 |
| `assembly_category_billings` | 计费管理 | 这个分类启用了哪些费用 | 分类一侧一对多 |

从分类看是一对多：一个分类有多条计费行，每条计费行只挂一个费用。费用档案是共用字典，同一费用可以出现在多个分类下，那是多条计费行，费用定义仍只有一行。

```text
assembly_categories 1 ──< assembly_category_billings >── 1 fee_archives

冲压件 ── 计费行 ── 运输
       └─ 计费行 ── 管理费
总成件 ── 计费行 ── 运输
       └─ 计费行 ── 管理费
       └─ 计费行 ── 税前利润
```

上面只说明一对多的形状。空库实际勾选见 §7.3：四个分类都选用现网那六项。同一分类下，同一费用只允许一条计费。

---

## 3. 定稿

| # | 决定 |
|---|------|
| D1 | 三张表都在 `masterdata`。分类与费用是绝对上游；计费只组合这两张表 |
| D2 | 分类、费用是列表 + 抽屉。计费管理是左分类列表、右费用表，勾选后一次保存。无上传、无年月、无基地、无项目。侧栏只在「主数据」下增加一个二级菜单「总成计费」，三页是它的叶子 |
| D3 | 分类、费用用整数 `id` 做主键。稳定业务键是 `code`，创建后不改。页面主字是 `name` |
| D4 | 计费行的外键指向两张父表的 `id`，`ondelete` 与 `onupdate` 都是 `RESTRICT` |
| D5 | 父表 Model 不 `relationship`、不 import 计费。计费 Model 可以 `relationship` 指回分类和费用 |
| D6 | 删除分类或费用时，若仍有计费行，动态引用检查拒绝，文案「仍被引用，不能删除」。先到计费管理删对照 |
| D7 | 启用 / 禁用只改 `is_enabled`。禁用后不能被新计费选中；已有计费行留着，列表标已禁用 |
| D8 | 计费率在费用档案，列 `charge_rate`。每条费用必填，全库这一种费只有这一个率。计费行不复制费率、不存金额 |
| D9 | 空库种子按现网总成核价勾选：四个分类都选用运输、仓储+包装、财务费、管理费、报废费用、税前利润。已有计费行则不覆盖。检具、器具不在费用档案里，不进种子 |
| D10 | 分类通过计费行选用费用，计算时读费用档案上的 `charge_rate`。同一费用要按分类用不同百分数时，再在计费行加列；在那之前改档案率，所有选用该费用的分类一起变 |

依赖：

```text
写入
  三个主数据页  →  各切片 CRUD

读取（本期无下游接入）
  以后 costing / bom / stamping
      →  masterdata 对应 Service

禁止
  masterdata → costing / bom / stamping / yishiyiyi
  下游往这三张表插行
  用采购对象 object_kind、焊信工艺名、I1～I8 代码代替这三张表
```

---

## 4. 和现网口径分开

| 现网 | 本设计 |
|------|--------|
| 采购对象 `object_kind`：`l0_degenerate` / `l1_subassembly` / `l1_stamping` | 总成分类是另一维。冲压件、凸焊件、总成件、黑漆件不映射成 `object_kind` |
| 焊信里的「凸焊」「电泳黑漆」 | 工艺项目。黑漆件是分类名，不从焊信拆行，不自动打标 |
| 间接 I1 单件运输、I2 仓储费+捆包费 | 费用档案写「运输」「仓储+包装」。名称按本档案，不改现网列名 |
| 管理费、财务费、报废费用、税前利润、仓储+包装 = 基数 × `system_configs` 费率 | 费用档案自带计费率。本期核算仍读系统设置，不读 `charge_rate`。改档案不回写系统设置 |
| 包装运输上传 `bom_packaging_transport_fees` | 单件金额档案不动。本费用档案存的是计费率，不存单价 |

检具分摊、器具分摊不进首期种子。要计时，在费用档案加行，再在计费管理勾到对应分类。

---

## 5. 总成分类 `assembly_categories`

### 5.1 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Integer PK | ✓ | 关联只用它 |
| `code` | String(50) | ✓ | 稳定键。创建后不改。小写英文和下划线 |
| `name` | String(50) | ✓ | 页面主字。可改，全表唯一 |
| `sort_order` | Integer | ✓ | 列表顺序。手填 |
| `is_enabled` | Boolean | ✓ | 默认启用 |
| `remark` | Text | | |
| AuditUserMixin | | ✓ | `created_at` / `created_by` / `updated_at` / `updated_by` |

### 5.2 约束

```text
PK:     id
UNIQUE: code          -- uix_assembly_category_code
UNIQUE: name          -- uix_assembly_category_name
Index:  sort_order, is_enabled
```

### 5.3 空库种子

表为空时写入。已有任意行则跳过，不覆盖。

| sort_order | code | name |
|------------|------|------|
| 1 | `stamping` | 冲压件 |
| 2 | `projection_weld` | 凸焊件 |
| 3 | `assembly` | 总成件 |
| 4 | `black_paint` | 黑漆件 |

四行都启用。再加分类走页面，例如以后的新种类，不改这四行的 `code`。

---

## 6. 费用档案 `fee_archives`

### 6.1 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Integer PK | ✓ | |
| `code` | String(50) | ✓ | 稳定键。创建后不改 |
| `name` | String(50) | ✓ | 页面主字。可改，全表唯一 |
| `charge_basis` | String(20) | ✓ | `amount` 金额，或 `rate` 比例。创建后可改。两种口径都要填计费率 |
| `charge_rate` | Numeric(8, 6) | ✓ | **计费率。** 小数，与系统费率同形：`0.02` = 2%，`0.03` = 3%。范围 0～1（0%～100%） |
| `sort_order` | Integer | ✓ | |
| `is_enabled` | Boolean | ✓ | 默认启用 |
| `remark` | Text | | |
| AuditUserMixin | | ✓ | |

`charge_basis` 只允许这两个字面量。页面用下拉：金额 / 比例。

计费率库内用小数，接口出入用小数字符串（`"0.02"`）。页面按百分数显示和录入：框里填 `2` 表示 2%，提交前除以 100；禁止把 `2` 当成 200% 落成 `2`。量化到小数点后六位（与系统费率 `Q6` 相同）。`0` 表示 0%，允许。大于 100% 拒绝。千分之 3 在本页填 `0.3`（即 0.3%），不另做千分号输入。

### 6.2 约束

```text
PK:     id
UNIQUE: code          -- uix_fee_archive_code
UNIQUE: name          -- uix_fee_archive_name
Index:  sort_order, is_enabled
```

### 6.3 空库种子

| sort_order | code | name | charge_basis | charge_rate | 页面 |
|------------|------|------|----------------|-------------|------|
| 1 | `warehouse_packaging` | 仓储+包装 | `amount` | `0.01` | 1% |
| 2 | `transport` | 运输 | `amount` | `0.02` | 2% |
| 3 | `management` | 管理费 | `rate` | `0.02` | 2% |
| 4 | `financial` | 财务费 | `rate` | `0.02` | 2% |
| 5 | `scrap` | 报废费用 | `rate` | `0.003` | 0.3%（3‰） |
| 6 | `pretax_profit` | 税前利润 | `rate` | `0.02` | 2% |

仓储+包装、管理费、财务费、报废费用、税前利润的初值与系统设置现网默认相同（`finished_warehouse_packaging_rate` 1%，管理费、财务费、税前利润各 2%，报废费用 `finished_scrap_rate` 3‰）。运输在系统设置里没有对应费率，种子先写 2%。报废费用的库内小数是 `0.003`；本页按百分数显示为 0.3%，不另做千分号。六行都是空库初值，上线前在费用档案页改成业务要的百分数。已有任意行则整表跳过，不覆盖已改过的率。

---

## 7. 计费管理 `assembly_category_billings`

一条计费 = 一个分类选用了一个费用。

### 7.1 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | Integer PK | ✓ | |
| `assembly_category_id` | Integer FK | ✓ | → `assembly_categories.id` |
| `fee_archive_id` | Integer FK | ✓ | → `fee_archives.id` |
| `remark` | Text | | 页面不编辑。仍勾着的行保留原备注 |
| AuditUserMixin | | ✓ | |

### 7.2 约束

```text
PK:     id
FK:     assembly_category_id
        REFERENCES assembly_categories(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT
FK:     fee_archive_id
        REFERENCES fee_archives(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT
UNIQUE: (assembly_category_id, fee_archive_id)
        -- uix_assembly_category_billing_pair
Index:  assembly_category_id, fee_archive_id
```

分类和费用都是独立主数据，计费不是某一张的附属明细，所以两条外键都是 `RESTRICT`，不用 `CASCADE`。改的是整数主键，实际不会改主键；`onupdate` 仍要声明。

页面按分类整批保存勾选。勾选即选用，取消勾选即删除这条对照。顺序跟费用档案的 `sort_order`。已有行若仍勾着，备注留着。对照行没有自己的启用开关。

停用的分类不能改勾选。停用的费用不能新勾上；已经勾过的可以保持，也可以取消。同一对重复 → `BusinessException(..., code=409)`。

### 7.3 空库种子

计费表为空时写入。已有任意计费行则整表跳过，不覆盖页面上改过的勾选。分类或费用字典里找不到对应 `code` 时跳过这一对。

现网总成核价每张卡都计这六项（I1 运输、I2 仓储+包装、I3 财务费、I4 管理费、I5 报废费用、I6 税前利润）。四个分类同一套勾选。检具（I7）、器具（I8）不在费用档案里，不进种子。

| 分类 | 费用 |
|------|------|
| 冲压件、凸焊件、总成件、黑漆件 | 仓储+包装、运输、管理费、财务费、报废费用、税前利润 |

顺序跟费用档案的 `sort_order`。备注空。

---

## 8. 写入规则

分类和费用是本切片的增删改。计费只有查看和整批保存勾选。

| 操作 | 规则 |
|------|------|
| 新增 | `code`、`name` 必填。`code` 去首尾空格后转小写，只保留 `[a-z][a-z0-9_]*`。`name` 去首尾空格。冲突 409 |
| 编辑分类 / 费用 | 可改 `name`、`sort_order`、`is_enabled`、`remark`。费用还可改 `charge_basis`、`charge_rate`。`code` 不接受修改 |
| 保存勾选 | `PUT …/category-billings/categories/{id}`，请求体是 `fee_archive_ids`。一次替换该分类的选用。空列表表示这一类不计费 |
| 禁用 | 只影响能否被新选。不级联禁用另一张表 |
| 取消勾选 | 删除这条对照。没有逐条新增、修改、删除接口 |
| 删除分类或费用 | 仍被计费引用则拒绝。提示落到计费管理。分类 Service、费用 Service 不 `count` 计费表 |
| 空库种子 | 分类、费用、计费三张表都灌。计费见 §7.3。已有行不覆盖 |

启用 / 禁用是非主键修改，外键不拦截。

---

## 9. 产品入口

侧栏在「主数据」下只增加 **一个二级菜单「总成计费」**（对齐项目：父级无页面、无 hash）。总成分类、费用档案、计费管理是它展开后的三片叶子，顺序固定。三页不与基地、钢厂并列，也不另开一级分组。

```text
主数据
  基地
  项目
  供应商
  牌号分类
  钢厂
  总成计费          ← 唯一新增的二级菜单，无 hash
    总成分类
    费用档案
    计费管理
```

权限树同一形状。`menu:assembly-billing` 的 `type` 是 `group`，挂在 `menu:masterdata` 下；三叶的 `type` 是 `menu`，只出现在这个 group 的 `children` 里。

```text
menu:masterdata
  menu:assembly-billing          总成计费（group）
    menu:assembly-category       总成分类
    menu:fee-archive             费用档案
    menu:category-billing        计费管理
```

| 页 | Hash | 权限菜单 | API |
|----|------|----------|-----|
| 总成分类 | `#/assembly-category` | `menu:assembly-category` | `/api/masterdata/assembly-categories` |
| 费用档案 | `#/fee-archive` | `menu:fee-archive` | `/api/masterdata/fee-archives` |
| 计费管理 | `#/category-billing` | `menu:category-billing` | `/api/masterdata/category-billings`；保存勾选 `PUT …/categories/{id}` |

总成分类、费用档案：`view` / `create` / `update` / `delete`。计费管理：`view` / `update`（保存勾选）。本期不做导出、不做导入。

侧栏 HTML 插在「钢厂」之后，嵌套 class 抄项目（`submenu-item has-submenu` + `submenu-nested`）。父链接 `javascript:void(0)`，`data-submenu-toggle="assemblyBillingSubmenu"`。三片叶子才带 hash。

面包屑：`['主数据', '总成计费', '总成分类']`，费用档案、计费管理同理。

列表：HUD 密表，默认 `sort_order`，其次 `code`。分类页、费用页用名称模糊搜索，启用状态胶囊。费用页列出计费率，显示为 `2%`、`3%`。

计费页左边是总成分类列表，右边是费用表。表上勾选，表头可全选。计费率、口径从费用档案带出，本页只读。点一次「保存」写入当前分类的勾选；切到别的分类时若还没保存，先确认。保存走 `op:category-billing:update`。停用的分类只读。

抽屉：分类和费用是单表表单。费用抽屉的计费率按百分数填。计费页不用抽屉。

无对应 `menu:` 时藏叶子。三叶都无权限则空「总成计费」一并隐藏。落地时 `catalog.json`、`static/index.html` 侧栏、`features/index.js` 的 `pageMeta` 三处用同一棵树。

---

## 10. 落地时的代码位置

已按垂直切片落地，跟现有主数据单页（牌号、钢厂）对齐：

```text
app/models/masterdata/assembly_category.py
app/models/masterdata/fee_archive.py
app/models/masterdata/category_billing.py

app/repositories/masterdata/assembly_category.py
app/repositories/masterdata/fee_archive.py
app/repositories/masterdata/category_billing.py

app/services/masterdata/assembly_category/service.py
app/services/masterdata/fee_archive/service.py
app/services/masterdata/category_billing/service.py

app/routers/masterdata/assembly_category.py
app/routers/masterdata/fee_archive.py
app/routers/masterdata/category_billing.py

static/js/features/masterdata/assembly-category/
static/js/features/masterdata/fee-archive/
static/js/features/masterdata/category-billing/
```

Router 只取参、调本表 Service、用工厂返回 VO。路径参数写成 `/{record_id:int}`。分页参数 `page` + `size`。错误只抛 `NotFoundException` / `BusinessException`。

`schema_comment` 三行中文名：总成分类、费用档案、计费管理。分类与费用的 `ref_hint` 指向「主数据 / 总成计费 / 计费管理」。

Model 注册进 `app/models/masterdata/__init__.py`，供 `create_all`。业务代码从具体模块 import。

---

## 11. 本期不做

| 项 | 留到以后 |
|----|----------|
| 总成核价按分类决定算哪些间接费 | 核算另做设计，读计费 Service |
| 核算改读费用档案上的计费率 | 本期仍用系统设置里的费率。见 §4 |
| BOM 节点、采购对象、冲压零件外键指向分类 | 那时由引用方声明 `RESTRICT` |
| 按基地、项目、年月做不同计费 | 本期全库一套对照 |
| Excel 上传 | 行数是十行级，只手工维护 |
| 检具、器具进种子 | 需要时加费用行再勾选 |

---

## 12. 修订

| 日期 | 说明 |
|------|------|
| 2026-11-06 | 初稿。三表、四分类、五费用、计费一对多。未编码 |
| 2026-11-06 | 菜单：主数据下只挂一个二级菜单「总成计费」，三页是它的叶子 |
| 2026-11-06 | 费用档案增加计费率 `charge_rate`（小数，页面按 2%、3% 录入）。计费行不另存率 |
| 2026-11-06 | 落地三表、三个维护页，以及主数据下二级菜单「总成计费」 |
| 2026-11-06 | 计费管理改为左分类列表、右费用勾选，一次保存 |
| 2026-11-06 | 空库按现网五项给四个分类全部勾上，初始化不用再手录 |
| 2026-11-06 | 计费只留整批勾选。去掉逐条增删改、两个多余权限码，以及对照行上的顺序和启用 |
| 2026-11-09 | 费用档案与四个分类的空库种子加入报废费用（`scrap`，`0.003` = 3‰），对齐现网总成核价 I5。检具、器具仍不进种子 |
