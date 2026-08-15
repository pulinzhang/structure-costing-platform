# 汽车冲压件自动核价平台

> 基于 FastAPI + SQLite 的汽车冲压件核价系统，支持零件管理、工艺上传、成本核算、报价生成。

## 设计风格

**Brabus Carbon & Precision Dark** — 碳素黑 · 钛灰面板 · 标志性红 · 锐利线条

---

## 架构说明

**前后端分离 SPA 架构**

| 层级 | 说明 |
|------|------|
| **后端** | FastAPI API Server（端口 8000），仅提供 JSON API |
| **前端** | 原生 JavaScript SPA（`static/index.html`），通过 Hash 路由 |
| **交互** | Bootstrap JS（Modal、Dropdown 等），Tailwind CSS（样式） |

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.109+ |
| 数据库 | SQLite + SQLAlchemy 2.0 |
| 前端 | 原生 HTML/CSS/JavaScript (SPA) |
| 样式 | Tailwind CSS + 自定义 CSS 变量 |
| 数据处理 | Pandas, OpenPyXL |
| 部署 | Uvicorn |

---

## 项目结构

```
stamping-costing-platform/
├── app/
│   ├── config.py              # 配置管理
│   ├── database.py            # 数据库配置
│   ├── routers/               # API 路由层（垂直切片）
│   │   ├── dashboard/         # 仪表盘
│   │   │   └── crud.py        # GET /api/dashboard/*
│   │   ├── stamping/          # 冲压工艺
│   │   │   ├── crud.py        # 零件/工序 CRUD API（/api/stamping/parts/*）
│   │   │   ├── upload.py      # 文件上传 API
│   │   │   └── tonnage_price.py # 吨位单价维护 API
│   │   ├── costing/           # 成本核算
│   │   │   └── crud.py        # POST /api/costing/calculate
│   │   ├── quotation/         # 报价管理
│   │   │   └── crud.py        # GET /api/quotation/*
│   │   └── settings/          # 系统设置
│   │       └── crud.py        # GET/PUT /api/settings/*
│   ├── services/              # 业务逻辑层
│   │   └── stamping/
│   │       ├── stamping_service.py
│   │       └── upload/        # 上传服务
│   ├── repositories/          # 数据访问层
│   │   └── stamping/
│   │       └── stamping_repository.py
│   ├── models/                # 数据库模型
│   │   └── stamping.py        # StampingPart, StampingProcess
│   ├── schemas/               # Pydantic DTO
│   │   └── stamping.py
│   ├── parsers/               # Excel 解析器
│   │   └── stamping/
│   │       └── stamping_parser.py
│   └── utils/                 # 工具函数
│       ├── logging_config.py
│       ├── response.py
│       └── db_migration.py
├── static/                    # 静态资源（SPA 前端）
│   ├── index.html             # SPA 入口
│   ├── css/
│   │   └── style.css          # 全局样式 + Brabus 变量
│   └── js/
│       ├── app.js             # SPA 主应用（Hash 路由）
│       ├── main.js            # 公共工具（HttpClient、Toast）
│       └── features/          # 功能模块
│           ├── index.js       # 页面元数据
│           ├── dashboard/
│           ├── stamping/
│           │   ├── upload/
│           │   └── parts/
│           ├── costing/
│           ├── quotation/
│           └── settings/
├── docs/                      # 文档
│   ├── front-end.mdc          # 前端开发规范
│   ├── architecture-constitution.mdc  # 架构宪法
│   └── naming-convention.mdc  # 命名规范
├── data/                      # SQLite 数据库
│   └── stamping_costing.db
├── uploads/                   # 上传文件（简图）
├── logs/                      # 日志文件
├── main.py                    # 应用入口
└── requirements.txt           # Python 依赖
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

服务启动后访问：
- **前端页面**：http://localhost:8000/app
- **API 文档**：http://localhost:8000/docs

### 3. 开发前端（可选）

使用 Live Server 打开 `static/index.html`，配合后端 API 使用。

---

## API 路由

| Tag | 方法 | 路径 | 说明 |
|-----|------|------|------|
| **仪表盘** | GET | `/api/dashboard/stats` | 全局统计 |
| | GET | `/api/dashboard/stats/parts` | 零件数量 |
| | GET | `/api/dashboard/stats/processes` | 工序数量 |
| | GET | `/api/dashboard/stats/models` | 车型数量 |
| **冲压工艺** | GET | `/api/stamping/parts/list` | 零件列表（分页） |
| | GET | `/api/stamping/parts/{part_id}` | 零件详情 |
| | DELETE | `/api/stamping/parts/{part_id}` | 删除零件 |
| | PATCH | `/api/stamping/processes/{process_id}` | 更新工序 |
| | PUT | `/api/stamping/parts/{part_id}/processes` | 批量更新工序 |
| **冲压工艺上传** | POST | `/api/stamping/upload/` | 上传工艺文件 |
| **核价** | POST | `/api/costing/calculate` | 成本计算 |
| **报价** | GET | `/api/quotation/list` | 报价列表 |
| **系统设置** | GET | `/api/settings/system/config` | 获取配置 |
| | PUT | `/api/settings/system/config` | 更新配置 |

---

## 配置说明

通过 `app/config.py` 或 `.env` 文件配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `APP_ENV` | 运行环境 | `development` |
| `HOST` | 服务地址 | `127.0.0.1` |
| `PORT` | 服务端口 | `8000` |
| `DATABASE_URL` | 数据库连接 | `sqlite:///./data/stamping_costing.db` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `DEBUG` | 调试模式 | `True` |

### 环境差异

| 环境 | 调试模式 | 日志级别 | CORS |
|------|----------|----------|------|
| `development` | ✅ | DEBUG | 允许所有 |
| `production` | ❌ | WARNING | 白名单 |
| `test` | ✅ | DEBUG | 允许所有 |

---

## 数据模型

### StampingPart（冲压零件）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| part_number | String | 零件号 |
| part_name | String | 零件名称 |
| vehicle_model | String | 车型 |
| version | String | 版本 |
| material | String | 材料 |
| thickness | Float | 料厚 (mm) |
| part_weight | Float | 零件重量 (kg) |
| sketch_url | String | 简图路径 |

### StampingProcess（冲压工序）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| part_id | Integer | 零件 ID（外键） |
| process_seq | String | 工序序号（如 OP10） |
| process_code | String | 工序代码（如 拉伸） |
| die_type | String | 模具类型 |
| tonnage | Float | 吨位 |
| press_time | Float | 冲压时间 (s) |
| labor_time | Float | 人工时间 (min) |

---

## 开发指南

### 前端开发规范

详见 [docs/front-end.mdc](docs/front-end.mdc)：

- 使用 **Tailwind CSS** 原子类
- 使用 **Brabus 深色变量**（`bg-[#0a0a0a]`、`text-[#9e9e9e]` 等）
- 禁止使用 Bootstrap 类名
- 页面通过 JavaScript 模板字符串渲染

### 后端开发规范

详见 [docs/architecture-constitution.mdc](docs/architecture-constitution.mdc)：

- **Router** → 接收请求，调用 Service
- **Service** → 业务逻辑，调用 Repository/Parser
- **Repository** → 数据库 CRUD
- **Parser** → Excel 解析（纯函数）

### API 调用示例

```javascript
// 获取零件列表
const result = await HttpClient.get('/api/stamping/parts/list', {
    params: { vehicle_model: 'T28', version: '1.0', skip: 0, limit: 20 }
});

// 上传工艺文件
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('vehicle_model', 'T28');
formData.append('version', '1.0');
const result = await HttpClient.post('/api/stamping/upload/', formData);

// 成本计算
const result = await HttpClient.post('/api/costing/calculate', {
    data: { part_ids: [1, 2, 3] }
});
```

---

## 项目规范

| 规范 | 说明 |
|------|------|
| [命名规范](docs/naming-convention.mdc) | 变量、函数、类、文件的命名规则 |
| [前端规范](docs/front-end.mdc) | Tailwind CSS + Brabus 风格 |
| [架构宪法](docs/architecture-constitution.mdc) | 分层架构与依赖方向 |

---

## 许可证

MIT License
