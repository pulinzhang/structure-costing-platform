# 汽车冲压件自动核价平台 - 架构设计

> 适合初学者的分层架构指南

---

## 1. 项目概述

| 项目 | 说明 |
|------|------|
| 名称 | 汽车冲压件自动核价平台 |
| 技术栈 | FastAPI + SQLAlchemy + SQLite |
| 做什么 | 接收冲压工艺 Excel 文件，自动解析、存储并提供查询 |
| 核心流程 | 上传 Excel → 解析工序数据 → 保存简图 → 落库 → 返回结果 |

---

## 2. 分层架构（核心概念）

### 什么是"分层"？

就像一家餐厅：
- **服务员（Router）**：接收顾客点餐，只负责传话
- **厨师（Service）**：决定怎么做菜，处理具体业务
- **仓库管理员（Repository）**：从冰箱（数据库）取食材、存食材
- **冰箱（Database）**：真正存放数据的地方

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│  用户浏览器 / Postman / 前端                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Router（路由层）← 门卫                                    │
│  • 接收请求                                                │
│  • 验证参数                                                 │
│  • 调用 Service                                             │
│  • 返回响应                                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Service（服务层）← 厨师                                   │
│  • 处理业务逻辑                                             │
│  • 协调多个操作                                             │
│  • 数据转换                                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Repository（仓库层）← 仓库管理员                          │
│  • 数据库 CRUD 操作                                        │
│  • 增删改查                                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Database（数据库）← 冰箱                                  │
│  • 存储数据                                                │
│  • SQLite 文件                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构

```
stamping-costing-platform/
│
├── main.py                    # 程序入口，启动 FastAPI 服务器
│
├── app/
│   ├── config.py              # 程序配置（环境变量、路径等）
│   ├── database.py            # 数据库连接配置
│   │
│   ├── models/                # 模型层（数据库表结构）
│   │   └── stamping.py        # 定义零件、工序表结构
│   │
│   ├── schemas/               # Schema 层（请求/响应格式）
│   │   └── stamping.py        # 定义 API 参数和返回值格式
│   │
│   ├── repositories/          # 仓库层（数据库操作）
│   │   └── stamping/
│   │       └── stamping_repository.py # 零件/工序数据库操作
│   │
│   ├── services/              # 服务层（业务逻辑）
│   │   └── stamping/
│   │       ├── stamping_service.py    # 零件业务逻辑
│   │       └── upload/                # 上传相关
│   │           └── stamping_upload.py # 上传业务逻辑
│   │
│   ├── routers/               # 路由层（HTTP 接口入口）
│   │   ├── dashboard.py       # 仪表盘
│   │   ├── parts/            # 零件管理
│   │   ├── costing/          # 核价
│   │   ├── quotation/        # 报价
│   │   ├── settings/         # 设置
│   │   └── stamping/         # 冲压工艺
│   │       ├── crud.py       # 零件查询接口
│   │       └── upload.py     # 文件上传接口
│   │
│   ├── parsers/               # 解析层（读文件）
│   │   └── stamping/
│   │       └── stamping_parser.py # 解析冲压工艺 Excel
│   │
│   └── utils/                 # 工具函数
│       ├── logging_config.py   # 日志配置
│       └── response.py        # 统一响应格式
│
├── uploads/                   # 上传文件存放
│   └── T28/                   # 按车型分目录
│       └── 1.0/              # 按版本分目录
│           ├── *.xlsx         # 上传的 Excel 文件
│           └── *.png          # 零件简图
│
├── data/                      # SQLite 数据库文件
│   └── stamping_costing.db    # 冲压核价数据库
│
└── logs/                      # 日志文件
│   └── app.log               # 应用运行日志
```

---

## 4. 为什么要分层？

### 初学者的困惑：为什么不把所有代码写在一起？

假设你要写一个查询零件的功能：

**方式 A：全部写在一起（不推荐）**

```python
@router.get("/parts")
def get_parts():
    # 1. 连接数据库
    engine = create_engine("sqlite:///...")
    Session = sessionmaker(bind=engine)
    db = Session()

    # 2. 查询数据
    parts = db.query(Part).all()

    # 3. 转换成字典
    result = [{"id": p.id, "name": p.name} for p in parts]

    # 4. 返回 JSON
    return {"data": result}
```

问题：
- 测试困难（无法单独测试查询逻辑）
- 代码复用困难
- 如果有多个接口都要查询 parts，代码要重复写
- 数据库配置散落在各处

**方式 B：分层（推荐）**

```python
# routers/stamping/crud.py
@router.get("/parts")
def get_parts():
    service = StampingPartService()
    return service.list_parts()  # 一行代码搞定
```

```python
# services/stamping_service.py
class StampingPartService:
    def list_parts(self):
        repo = StampingPartRepository()
        return repo.find_all()  # 只关心业务，不关心数据库细节
```

```python
# repositories/stamping_repository.py
class StampingPartRepository:
    def find_all(self):
        return db.query(Part).all()  # 只关心数据库操作
```

好处：
- 每层只做一件事
- 可以单独测试每层
- 代码可以复用
- 改数据库不影响业务逻辑

---

## 5. 各层详解

### 5.1 Router（路由层）

**职责：接收请求，返回响应**

```
用户请求 ──► Router ──► Service ──► Repository ──► Database
                │
                └──────────────────► 响应
```

**Router 的工作：**
1. 接收请求参数
2. 调用 Service
3. 把结果包装成 JSON 返回

**示例：**

```python
# app/routers/stamping/crud.py

from fastapi import APIRouter, Depends

router = APIRouter(prefix="/stamping", tags=["冲压"])

# 查询零件列表
@router.get("/parts")
def list_parts(
    vehicle_model: str,  # 接收参数
    version: str,
):
    # 调用 Service
    service = StampingPartService()
    data, total = service.list_parts(vehicle_model, version)

    # 返回响应
    return {
        "code": 0,
        "message": f"查询到 {total} 个零件",
        "data": data,
        "total": total,
    }
```

### 5.2 Service（服务层）

**职责：处理业务逻辑**

**Service 的工作：**
1. 组合多个 Repository 操作
2. 数据格式转换
3. 业务规则验证

**示例：**

```python
# app/services/stamping_service.py

class StampingPartService:
    """零件业务逻辑"""

    def __init__(self):
        self.repository = StampingPartRepository()

    def list_parts(self, vehicle_model, version):
        """
        获取零件列表
        这里可以加业务逻辑，比如：
        - 权限验证
        - 数据筛选
        - 格式转换
        """
        # 调用 Repository 查询数据
        parts, total = self.repository.paginate(
            vehicle_model=vehicle_model,
            version=version,
        )

        # 转换成字典格式返回
        return [p.to_dict() for p in parts], total
```

### 5.3 Repository（仓库层）

**职责：数据库操作（CRUD）**

> CRUD = Create（创建）、Read（读取）、Update（更新）、Delete（删除）

**Repository 的工作：**
1. 执行 SQL 查询
2. 增删改数据库记录

**示例：**

```python
# app/repositories/stamping_repository.py

class StampingPartRepository:
    """零件数据库操作"""

    def get_by_id(self, db, part_id):
        """查询单个零件"""
        return db.query(Part).filter(Part.id == part_id).first()

    def paginate(self, vehicle_model, version, skip=0, limit=100):
        """分页查询零件"""
        q = db.query(Part).filter(
            Part.vehicle_model == vehicle_model,
            Part.version == version,
        )
        total = q.count()
        parts = q.offset(skip).limit(limit).all()
        return parts, total
```

### 5.4 Model（模型层）

**职责：定义数据库表结构**

```python
# app/models/stamping.py

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship

class StampingPart(Base):
    """零件表"""
    __tablename__ = "stamping_parts"

    id = Column(Integer, primary_key=True)        # 主键
    part_number = Column(String(50), unique=True) # 零件号
    vehicle_model = Column(String(50))           # 车型
    version = Column(String(50))                 # 版本
    part_name = Column(String(200))              # 零件名称
    material = Column(String(50))                 # 材质
    thickness = Column(Numeric(10, 3))           # 料厚(mm)
    tonnage = Column(Numeric(10, 1))             # 冲压吨位(T)

    # 关联工序（一个零件有多个工序）
    processes = relationship("StampingProcess", back_populates="part")

class StampingProcess(Base):
    """工序表"""
    __tablename__ = "stamping_processes"

    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("stamping_parts.id"))  # 外键
    process_seq = Column(String(20))         # 工序序号（OP10、OP20...）
    process_order = Column(Integer)           # 顺序
    tonnage = Column(Integer)                 # 吨位
    remark = Column(Text)                      # 备注

    # 关联零件
    part = relationship("StampingPart", back_populates="processes")
```

**Model 就像：建筑图纸**，只定义有哪些字段，不包含任何操作。

**注意**：
- Model 里面可以有 `relationship`，表示表与表之间的关系
- 但不能有增删改查的代码，那些属于 Repository

### 5.5 Parser（解析层）

**职责：解析文件（如 Excel）**

**特点：纯函数，无副作用**

```python
# app/parsers/stamping_parser.py

def parse_stamping_excel(file_path):
    """
    输入：Excel 文件路径
    输出：解析后的数据
    """
    # 读取 Excel
    # 提取数据
    # 返回结构化结果
    return {
        "parts": [...],
        "processes": [...],
        "images": {...},
    }
```

---

## 6. 数据流向示例

以"上传冲压工艺 Excel"为例：

```
1. 用户上传 Excel
       │
       ▼
2. Router 接收请求
   • 验证文件类型
   • 提取车型、版本参数
       │
       ▼
3. Service 处理业务
   • 保存文件到磁盘
   • 解析 Excel
   • 保存简图
   • 调用 Repository 保存数据
       │
       ├──► Repository.save_parts() ──► Database
       │
       └──► Repository.save_processes() ──► Database
       │
       ▼
4. Router 返回结果
   {"success": true, "parts_count": 100, ...}
```

---

## 7. 快速导航

| 文件 | 层 | 做什么 |
|------|-----|--------|
| `app/routers/stamping/crud.py` | Router | 冲压工艺 HTTP 接口 |
| `app/routers/stamping/upload.py` | Router | 文件上传接口 |
| `app/services/stamping/stamping_service.py` | Service | 零件业务逻辑 |
| `app/services/stamping/upload/stamping_upload.py` | Service | 上传业务逻辑 |
| `app/repositories/stamping/stamping_repository.py` | Repository | 数据库增删改查 |
| `app/models/stamping.py` | Model | 数据库表定义 |
| `app/schemas/stamping.py` | Schema | 请求/响应格式 |
| `app/parsers/stamping/stamping_parser.py` | Parser | Excel 解析 |
| `app/database.py` | Database | 数据库连接 |
| `main.py` | - | 程序入口 |

---

## 8. 添加新功能的步骤

假设要添加"查询工序"功能：

```
Step 1: 定义 Schema（请求/响应格式）
    └── app/schemas/stamping.py
        └── class StampingProcessResponse(BaseModel): ...

Step 2: 扩展 Repository（数据库操作）
    └── app/repositories/stamping/stamping_repository.py
        └── class StampingProcessRepository:
            └── def get_by_part_id(...): ...

Step 3: 扩展 Service（业务逻辑）
    └── app/services/stamping/stamping_service.py
        └── class StampingProcessService:
            └── def get_by_part_id(...): ...

Step 4: 添加 Router（接口）
    └── app/routers/stamping/crud.py
        └── @router.get("/parts/{part_id}/processes"): ...

Step 5: 注册路由（已在 main.py 中通过 include_router 自动完成）
```

---

## 9. 常见问题

### Q: Service 和 Repository 有什么区别？

```
Service（服务层）：
• 包含业务逻辑
• 决定"做什么"
• 可以组合多个 Repository 操作

Repository（仓库层）：
• 只负责数据库操作
• 决定"怎么查"
• 单一职责：增删改查
```

### Q: 什么时候该加 Service？

- 需要组合多个数据库操作
- 需要做数据转换
- 需要验证业务规则
- 多个 Router 需要复用同一段逻辑

### Q: 什么时候该加 Repository？

- 任何需要操作数据库的时候
- 把 SQL 相关代码隔离在这里

### Q: 简单查询需要 Service 吗？

如果只有简单的单表查询，可以：
- Router → Repository → Database

但为了保持一致性和可扩展性，建议都加上 Service。
