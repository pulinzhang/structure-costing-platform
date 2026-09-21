# 钢价政策 Service（`yishiyiyi/policy`）

> 一事一议 · 厚度加减价政策业务层  
> 路径：`app/services/yishiyiyi/policy/`

采用「根门面 + 按关注点子包」组织，与 `app/services/costing/stamping_part_cost/` 一致。

---

## 1. 业务范围

承接「钢价政策 / 厚度加减价」业务逻辑，供 Router 调用：

| 能力 | 说明 |
|------|------|
| 政策主表 / 阶梯明细 CRUD | 列表、详情、增删改、按条件批量删除 |
| Excel 导入 | 校验上传 → 归档 → 解析 → 事务内按键写入 |
| 阶梯匹配 | 按厚度 / 宽度 / 锌层等命中加减价（核价链路使用） |
| Excel 导出 | 主子表扁平化查询 + 生成工作簿 |

**对外入口**：

```python
from app.services.yishiyiyi.policy.service import SteelPricePolicyService
```

禁止本包 `__init__.py` 再导出。业务调用方经门面访问；子包实现类仅供本切片内部使用。

---

## 2. 为什么这样组织

1. **按关注点分包**  
   CRUD、导入、匹配、导出职责不同，分开后定位成本低：导入看 `importing/`，区间算法看 `match/ladder_matcher.py`。

2. **门面只做委托**  
   `SteelPricePolicyService` 不写业务细节，只转发。对外能力清单在门面，细节在子包。

3. **纯逻辑与编排分离（匹配）**  
   `LadderMatcher` 不访问数据库，只做区间判断；`match/service` 负责查候选与 fallback。

4. **查询组装与 Excel 生成分离（导出）**  
   `export/service.py` 产出扁平行；`excel_exporter` 负责 openpyxl。样式变更不搅进数据查询。

5. **仍遵守项目分层**  
   子包是 Service 内部拆分，不是新的架构层。写库走 Repository；解析只由 importing 调 Parser；Router 不直接碰 Parser / Repository。

包名用 `importing/` 而非 `import/`：后者是 Python 关键字。

---

## 3. 目录结构

```text
app/services/yishiyiyi/policy/
├── README.md
├── __init__.py                       # 只作包标记，不汇总导出
├── service.py                        # 薄门面：只委托
├── crud/
│   ├── __init__.py
│   └── policy_crud.py                # 主表/明细 CRUD、批量删除、筛选统计
├── importing/
│   ├── __init__.py
│   └── service.py                    # 上传校验 + 批量导入
├── match/
│   ├── __init__.py
│   ├── service.py                    # 查候选 + fallback 编排（API 匹配）
│   ├── ladder_matcher.py             # 纯区间匹配（无 DB）
│   └── adjustment_common.py          # 钢厂/大类别名 + 加减价候选筛选（供本切片与 costing）
└── export/
    ├── __init__.py
    ├── service.py                    # 主子表扁平化、调导出器
    └── excel_exporter.py             # openpyxl 生成；含 format_interval
```

---

## 4. 依赖方向

```text
Router / 其它 Service
        │
        ▼
SteelPricePolicyService          （门面，无业务细节）
   ├── crud.SteelPricePolicyCrudService
   ├── importing.SteelPricePolicyImportService
   ├── match.SteelPricePolicyMatchService
   │         └── LadderMatcher
   └── export.SteelPricePolicyExportService
             └── SteelPricePolicyExporter
        │
        ▼
repositories.yishiyiyi.policy    （数据访问）
parsers.yishiyiyi.policy         （仅 importing 调用）
```

| 子包 | 负责 | 不负责 |
|------|------|--------|
| `crud/` | 分页、详情、主表明细增删改、条件批量删、count / 筛选项 | 导入、匹配、Excel 字节 |
| `importing/` | 文件校验、源文件归档、Parser 结果按唯一键写入、进度回调 | HTTP、阶梯区间算法 |
| `match/` | 候选政策查询、命中收集与排序、精确钢种失败时 fallback 通用政策 | 写库、导入 |
| `export/` | 导出查询扁平化、生成 xlsx | CRUD 写操作 |

门面可暴露 `service.repository`；优先走门面方法，避免调用方散落 Repository 访问。

---

## 5. 关键业务约定

### 5.1 导入（`importing`）

- 整批 **单事务**：失败全回滚。
- 唯一键已存在 → **先删后插**（同事务 flush，避免唯一约束冲突）。
- 导入前按年/月归档源文件（`save_steel_price_upload`，`FILE_KIND_POLICY`），便于与基准价文件成对核对。
- 进度通过 `ProgressCallback` 上报；进度写辅助库，不与本事务写锁耦合。

### 5.2 匹配（`match`）

- 全程 Decimal 比较；多命中按 `sort_order`、`id` 取最优。
- **Fallback**：精确 `grade_value` 无命中时，再查 `grade_value/grade_type` 为空的通用政策（多钢种共用一行价格的场景）。
- **加减价别名与候选筛选**（`adjustment_common`）：钢厂/大类别名、`filter_candidates` /
  `order_by_base_thickness` 等为上游稳定 API；`winning_thickness` 与下游
  `costing/steel_price` 共用，禁止再把匹配逻辑放进 costing 后反向依赖。

### 5.3 导出（`export`）

- `export/service.py` 负责行数据；`excel_exporter` 负责样式与工作簿。
- `format_interval` 可被其它切片复用：  
  `from app.services.yishiyiyi.policy.export.excel_exporter import format_interval`

---

## 6. 职责

| 模块 | 职责 |
|------|------|
| `crud/policy_crud.py` | 列表字段 / 写操作审计 |
| `importing/service.py` | 导入替换策略、进度分段 |
| `match/ladder_matcher.py` | 区间运算符、命中维度 |
| `match/adjustment_common.py` | 钢厂别名 / 加减价候选排序 |
| `match/service.py` | fallback 策略 |
| `export/excel_exporter.py` / `export/service.py` | 导出列、Excel 样式 |

约束：门面不堆业务逻辑；Router 不直接调 Parser；子包之间避免成环（共享逻辑抽 helpers，或由门面编排）。

---

## 7. 相关路径

| 层级 | 路径 |
|------|------|
| Router | `app/routers/yishiyiyi/policy/` |
| Service（本目录） | `app/services/yishiyiyi/policy/` |
| Repository | `app/repositories/yishiyiyi/policy/` |
| Parser | `app/parsers/yishiyiyi/policy/` |
| DTO / VO | `app/schemas/dto/steel_price_policy_dto.py`、`app/schemas/vo/steel_price_policy_vo.py` |
| 前端 | `static/js/features/yishiyiyi/policy/` |
| API 前缀 | `/api/yishiyiyi/policy` |
| 对照结构 | `app/services/costing/stamping_part_cost/`（`calc/` / `export/`） |
