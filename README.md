# 汽车冲压件自动核价平台

基于 FastAPI 构建的汽车冲压件自动核价系统，提供零件管理、成本核算、报价生成等功能。

## 功能特性

- **仪表盘** - 数据概览与统计分析
- **零件管理** - 冲压件信息维护
- **文件上传** - Excel/CSV 格式批量导入
- **成本核算** - 自动计算零件加工成本
- **报价生成** - 快速生成客户报价单
- **系统设置** - 系统参数配置

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.109+ |
| 数据库 | SQLite + SQLAlchemy 2.0 |
| 前端模板 | Jinja2 |
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
│   │       ├── crud.py       # 零件/工序 CRUD
│   │       └── upload.py     # 文件上传
│   ├── services/             # 业务逻辑层
│   │   └── stamping/         # 冲压工艺服务
│   │       ├── stamping_service.py
│   │       └── upload/
│   ├── repositories/          # 数据访问层
│   │   └── stamping/
│   ├── models/                # 数据库模型
│   ├── schemas/               # Pydantic DTO
│   ├── parsers/               # Excel 解析器
│   ├── utils/                 # 工具函数
│   ├── config.py              # 配置管理
│   └── database.py            # 数据库配置
├── templates/                  # Jinja2 模板
├── static/                     # 静态资源
├── docs/                       # 文档
├── data/                       # 数据库存储
├── logs/                       # 日志文件
├── uploads/                    # 上传文件
├── main.py                     # 应用入口
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

### 3. 启动服务

```bash
python main.py
```

服务启动后访问 http://localhost:8000

### 4. 开发模式热重载

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

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

## API 路由

- `GET /` - 首页（重定向到仪表盘）
- `/dashboard` - 仪表盘数据
- `/stamping/upload` - 文件上传接口
- `/stamping/parts` - 零件管理 API
- `/stamping/processes` - 工序管理 API
- `/costing` - 成本核算 API
- `/quotation` - 报价管理 API
- `/settings` - 系统设置 API

## 数据存储

- 数据库文件: `data/stamping_costing.db`
- 上传文件: `uploads/`
- 日志文件: `logs/`

## 许可证

MIT License
