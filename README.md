# 汽车冲压件自动核价平台

基于 FastAPI 构建的汽车冲压件自动核价系统，提供零件管理、成本核算、报价生成等功能。

## 架构说明

**前后端分离架构**

- **后端**：FastAPI API Server (端口 8000) - 仅提供 API 接口
- **前端**：静态 HTML + JavaScript SPA (通过 Live Server 或 nginx)

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.109+ |
| 数据库 | SQLite + SQLAlchemy 2.0 |
| 前端 | 原生 HTML/CSS/JavaScript (SPA) |
| 样式 | Tailwind CSS |
| 数据处理 | Pandas, OpenPyXL |
| 部署 | Uvicorn |

## 项目结构

```
stamping-costing-platform/
├── app/
│   ├── routers/              # API 路由
│   │   ├── dashboard.py      # 仪表盘
│   │   ├── costing/          # 成本核算
│   │   ├── parts/            # 零件管理
│   │   ├── quotation/        # 报价管理
│   │   ├── settings/         # 系统设置
│   │   └── stamping/         # 冲压工艺
│   │       ├── crud.py       # 零件/工序 API
│   │       └── upload.py     # 文件上传 API
│   ├── services/             # 业务逻辑层
│   │   └── stamping/         # 冲压工艺服务
│   ├── repositories/          # 数据访问层
│   │   └── stamping/
│   ├── models/               # 数据库模型
│   ├── schemas/               # Pydantic DTO
│   ├── parsers/              # Excel 解析器
│   ├── utils/                # 工具函数
│   ├── config.py             # 配置管理
│   └── database.py           # 数据库配置
├── static/                   # 静态资源 (SPA 前端)
│   ├── css/
│   ├── js/
│   └── index.html            # SPA 入口页面
├── docs/                     # 文档
├── data/                     # 数据库存储
├── logs/                     # 日志文件
├── uploads/                  # 上传文件
├── main.py                   # 应用入口
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

复制环境配置文件：

```bash
cp .env.example .env
```

根据需要修改 `.env` 中的配置项。

### 3. 启动后端 API 服务

```bash
python main.py
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后访问 http://localhost:8000

### 4. 启动前端

**方式一：使用 Live Server 插件（推荐开发模式）**

1. 在 VS Code 或 Cursor 中安装 "Live Server" 插件
2. 右键点击 `static/index.html`
3. 选择 "Open with Live Server"

**方式二：直接访问后端托管的页面**

访问 http://localhost:8000/app

## API 文档

启动后端后，访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/stats` | 仪表盘统计 |
| POST | `/api/stamping/upload/` | 上传冲压工艺文件 |
| GET | `/api/stamping/parts/list` | 获取零件列表 |
| GET | `/api/stamping/parts/{id}` | 获取零件详情 |
| DELETE | `/api/stamping/parts/{id}` | 删除零件 |
| POST | `/api/costing/calculate` | 计算成本 |
| GET | `/api/quotation/list` | 获取报价列表 |
| GET | `/api/settings/config` | 获取系统配置 |
| PUT | `/api/settings/config` | 更新系统配置 |

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| APP_ENV | 运行环境 | development |
| HOST | 服务地址 | 0.0.0.0 |
| PORT | 服务端口 | 8000 |
| DATABASE_URL | 数据库连接 | sqlite:///./data/stamping_costing.db |
| LOG_LEVEL | 日志级别 | INFO |
| DEBUG | 调试模式 | True |

## 环境差异

- **development**: 调试模式，日志级别 DEBUG
- **production**: 生产模式，日志级别 WARNING
- **test**: 测试模式，使用内存数据库

## 数据存储

- 数据库文件: `data/stamping_costing.db`
- 上传文件: `uploads/`
- 日志文件: `logs/`

## 开发指南

### 前端开发

1. 修改 `static/index.html` 或 `static/js/app.js`
2. 使用 Live Server 实时预览
3. 所有 API 调用通过 `HttpClient` 对象

### 后端开发

1. 修改 `app/` 下的路由、服务、模型等
2. 使用 `python main.py --reload` 热重载
3. 通过 `/docs` 测试 API

## 许可证

MIT License
