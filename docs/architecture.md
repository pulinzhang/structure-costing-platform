# 汽车冲压件自动核价平台 - 架构设计

## 1. 项目概述

| 项目 | 说明 |
|------|------|
| 名称 | 汽车冲压件自动核价平台 (Stamping Costing Platform) |
| 技术栈 | FastAPI + SQLAlchemy + SQLite + Jinja2 |
| 定位 | B/S 架构的 Web 应用，接收冲压工艺 Excel 文件，自动解析、存储并提供查询 |
| 核心流程 | 上传 Excel → 解析工序数据 → 保存简图 → 落库 → 返回结果 |

---

## 2. 分层架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Router (路由层)                           │
│  职责：接收 HTTP 请求、参数验证、调用 Service、返回响应          │
│  特点：只做"门卫"，不写业务逻辑                               │
│  文件：app/routers/**/*.py                                   │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Service (服务层)                           │
│  职责：处理所有业务逻辑（文件 IO、数据库操作、业务规则）         │
│  特点：应用的"厨师"，做具体工作                               │
│  文件：app/services/**/*.py                                  │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Parser (解析层)                            │
│  职责：解析特定格式的文件（如 Excel）                          │
│  特点：纯函数，无状态，输入文件路径，输出结构化数据              │
│  文件：app/parsers/**/*.py                                   │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Model (模型层)                             │
│  职责：定义数据库表结构与 Python 对象的映射                     │
│  特点：只定义结构，不包含业务逻辑                              │
│  文件：app/models/**/*.py                                    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Database (数据库层)                        │
│  职责：数据库连接、会话管理、初始化                            │
│  特点：基础设施层                                             │
│  文件：app/database.py                                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构

```
stamping-costing-platform/
│
├── main.py                    # 应用入口，创建 FastAPI 实例
│
├── app/
│   ├── config.py              # 配置管理（多环境支持）
│   │
│   ├── routers/                # 路由层（HTTP 入口）
│   │   ├── upload/
│   │   │   └── stamping.py     # 冲压工艺上传路由
│   │   ├── dashboard.py        # 仪表盘
│   │   ├── parts.py           # 零件查询
│   │   ├── costing.py          # 核价
│   │   ├── quotation.py       # 报价
│   │   └── settings_router.py # 设置
│   │
│   ├── services/               # 服务层（业务逻辑）
│   │   └── upload/
│   │       └── stamping_upload.py  # 冲压上传服务
│   │
│   ├── parsers/                # 解析层（文件解析）
│   │   └── stamping_parser.py  # Excel 解析器
│   │
│   ├── models/                 # 模型层（数据库表结构）
│   │   └── stamping.py        # StampingPart / StampingProcess
│   │
│   ├── database.py             # 数据库连接
│   │
│   └── utils/                  # 工具函数
│       └── logging_config.py   # 日志配置
│
├── templates/                  # Jinja2 HTML 模板
├── static/                     # 静态资源
├── uploads/                    # 上传文件存储
├── logs/                       # 日志文件
└── data/                       # 数据库文件
```

---

## 4. 数据模型

### 4.1 零件主表 (StampingPart)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，自增 |
| vehicle_model | String | 车型 |
| version | String | 版本 |
| part_number | String | 零件号（全局唯一） |
| part_name | String | 零件名称 |
| material | String | 材质 |
| thickness | Numeric | 料厚(mm) |
| part_weight | Numeric | 零件重量(kg) |
| tonnage | Numeric | 冲压设备吨位(T) |
| process_method | String | 工艺方法 |
| sketch_url | String | 零件简图 URL |
| ... | | |

### 4.2 工序子表 (StampingProcess)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，自增 |
| part_id | Integer | 外键，关联零件 |
| process_seq | String | 工序序号（如 OP10） |
| process_order | Integer | 零件内工序顺序 |
| process_code | String | 工序代码 |
| tonnage | Integer | 设备吨位(T) |
| cost_ratio | Numeric | 费用比例 |
| remark | Text | 备注 |

---

## 5. 核心流程

### 5.1 上传解析流程

```
用户上传 Excel
    │
    ▼
Router: 验证参数（车型、版本、文件类型、文件大小）
    │
    ▼
Service.process_upload():
    │
    ├── 1. 保存文件到 uploads/车型/版本/
    │
    ├── 2. parse_stamping_excel() 解析 Excel
    │       │
    │       ├── 提取零件列表
    │       ├── 提取工序列表
    │       └── 提取简图（嵌入在 Excel 中的图片）
    │
    ├── 3. 保存零件简图到磁盘
    │
    ├── 4. _save_parts() 批量保存零件到数据库
    │       └── 先删除同车型同版本的旧数据
    │
    └── 5. _save_processes() 批量保存工序到数据库
            │
            └── 建立零件-工序关联
```

---

## 6. 各层职责详解

### 6.1 Router 层（路由层）

**设计原则：瘦路由，厚服务**

```
Router 的三件事：
1. 接收请求 → 从请求中提取参数
2. 调用 Service → 把参数传给业务层
3. 返回响应 → 把 Service 的结果封装成 HTTP 响应
```

**示例对比：**

```python
# ❌ 路由承担了业务逻辑（违反单一职责）
@router.post("/")
async def upload(...):
    content = await file.read()
    # 保存文件... ← 业务逻辑
    service = StampingUploadService(db)
    result = service.process_file(file_path, ...)  # 只传路径
    return {"success": True, ...}

# ✓ 路由只做验证和转发
@router.post("/")
async def upload(...):
    content = await file.read()
    service = StampingUploadService(db)
    result = service.process_upload(
        file_content=content,      # 传递内容而非路径
        filename=file.filename,
        vehicle_model=vehicle_model,
        version=version,
    )
    return JSONResponse({"success": True, "data": result})
```

### 6.2 Service 层（服务层）

**设计原则：高内聚，每个 Service 类对应一个业务场景**

```python
class StampingUploadService:
    """冲压工艺上传服务"""

    def process_upload(self, file_content, filename, vehicle_model, version):
        """完整业务流程"""
        # 1. 保存文件
        # 2. 解析 Excel
        # 3. 保存简图
        # 4. 保存零件
        # 5. 保存工序
        ...

    def _save_part_images(self, images, target_dir):
        """私有方法：保存简图"""
        ...

    def _save_parts(self, parts_data, ...):
        """私有方法：保存零件"""
        ...

    def _save_processes(self, processes_data, part_map):
        """私有方法：保存工序"""
        ...
```

### 6.3 Parser 层（解析层）

**设计原则：纯函数，无状态，可测试**

```python
# 输入：文件路径
# 输出：结构化数据
# 副作用：无（不写文件，不操作数据库）
ParseResult = namedtuple('ParseResult', [
    'parts',           # List[Dict]
    'processes',       # List[Dict]
    'images_by_part',  # Dict[part_number -> bytes]
    'warnings',        # List[str]
    'parse_time_ms',   # float
])

def parse_stamping_excel(file_path: str) -> ParseResult:
    """解析冲压工艺 Excel 文件"""
    ...
    return ParseResult(...)
```

### 6.4 Model 层（模型层）

**设计原则：只定义数据结构，不含业务逻辑**

```python
class StampingPart(Base):
    """冲压件主表"""
    __tablename__ = "stamping_parts"

    id = Column(Integer, primary_key=True)
    part_number = Column(String(50), unique=True)
    vehicle_model = Column(String(50))
    # ... 只定义字段
```

---

## 7. 配置管理

采用环境变量 + Pydantic Settings，支持多环境：

```python
# .env 文件
APP_ENV=development  # development | production | test

# 代码中使用
from app.config import settings
settings.DEBUG          # True
settings.DATABASE_URL   # sqlite:///...
settings.UPLOAD_DIR     # Path 对象
```

---

## 8. 日志管理

统一日志配置，按模块分层：

```python
# 不同模块使用不同的 logger name
logger = get_logger("main")           # 主模块
logger = get_logger("router.stamping") # 路由层
logger = get_logger("service.stamping_upload")  # 服务层

# 输出示例：
# 2026-07-17 15:30:00 - main - INFO - 应用启动完成
# 2026-07-17 15:30:01 - router.stamping - INFO - 接收到文件上传
# 2026-07-17 15:30:02 - service.stamping_upload - INFO - 上传处理完成
```

---

## 9. 为何这样设计？

### 9.1 瘦路由的好处

| 好处 | 说明 |
|------|------|
| 职责单一 | 路由只管 HTTP 相关的事 |
| 易于测试 | Service 层可以用单元测试覆盖，不依赖 HTTP |
| 代码复用 | 同一个 Service 可以被多个 Router 调用（如 API + CLI） |
| 易于维护 | 业务逻辑集中在 Service，改动时影响范围小 |

### 9.2 分层的好处

| 好处 | 说明 |
|------|------|
| 可测试 | Parser 是纯函数，Service 可以 mock DB |
| 可替换 | 换数据库只需改 Model 层 |
| 团队协作 | 路由、服务、解析可以分工开发 |

---

## 10. 扩展指南

### 添加新功能

```
1. 在 app/models/ 新建 model
2. 在 app/parsers/ 新建 parser（如果需要文件解析）
3. 在 app/services/ 新建 service
4. 在 app/routers/ 新建 router
5. 在 main.py 注册路由
```

### 添加新路由模块

```python
# app/routers/new_feature.py
from fastapi import APIRouter
router = APIRouter(prefix="/new-feature", tags=["New Feature"])

@router.get("/")
async def list_items():
    ...
```

```python
# main.py
from app.routers import new_feature_router
app.include_router(new_feature_router)
```

---

## 11. 快速导航

| 文件 | 行数 | 职责 |
|------|------|------|
| `main.py` | 1-149 | 应用入口，路由注册 |
| `app/routers/upload/stamping.py` | 1-99 | 冲压上传 HTTP 入口 |
| `app/services/upload/stamping_upload.py` | 1-260 | 冲压上传业务逻辑 |
| `app/parsers/stamping_parser.py` | - | Excel 解析 |
| `app/models/stamping.py` | 1-115 | 数据库模型定义 |
| `app/config.py` | 1-113 | 配置管理 |
| `app/database.py` | - | 数据库连接 |
| `app/utils/logging_config.py` | - | 日志配置 |
