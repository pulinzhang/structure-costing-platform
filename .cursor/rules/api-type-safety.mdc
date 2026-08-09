---
alwaysApply: true
description: FastAPI 后端类型安全、分层架构与 API 契约规范
---

# FastAPI 后端类型安全规范

> **核心原则**：Router Facade / Service 业务 / Repository 数据 / Model 表结构

---

## 1. API 响应契约

### 1.1 统一响应格式 `ApiResponse[T]`

```python
class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    success: bool = True
    message: str = "操作成功"
    data: T | None = None
```

### 1.2 方法选择

| 场景 | 方法 | code |
|------|------|------|
| 正常返回 | `ApiResponse.ok(data=vo)` | 200 |
| 创建资源 | `ApiResponse.created(data=vo)` | 201 |
| 更新资源 | `ApiResponse.updated(data=vo)` | 200 |
| 删除资源 | `ApiResponse.deleted()` | 200 |
| 业务异常 | `raise BusinessException(...)` | 4xx |
| 资源不存在 | `raise NotFoundException(...)` | 404 |
| 权限不足 | `raise PermissionException(...)` | 403 |
| 系统异常 | 全局处理器捕获 | 500 |

### 1.3 分页响应

```python
ApiResponse[PageResult[T]]  # 分页接口

class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
```

---

## 2. 分层职责

```
Router ──► Service ──► Repository ──► Database
   │         │            │
   │         │            └── SQLAlchemy Model
   │         └── 业务逻辑、VO 转换、事务管理
   └── ApiResponse[T]
```

| 层级 | 职责 | 禁止 |
|------|------|------|
| **Router** | 调用 Service、返回 ApiResponse | 查库、写业务逻辑 |
| **Service** | 业务逻辑、ORM→VO、事务 | 直接写 SQL |
| **Repository** | 数据库 CRUD | 写业务判断、commit |
| **Model** | 表结构定义 | 写业务方法 |

---

## 3. 各层返回类型

### 3.1 Repository → SQLAlchemy Model

```python
# ✅ 正确
def get_by_id(db, part_id) -> StampingPart | None
def paginate(db, ...) -> tuple[list[StampingPart], int]

# ❌ 禁止
def get_by_id(...) -> dict  # 禁止返回 dict
```

### 3.2 Service → VO / PageResult[VO]

```python
# ✅ 正确
def get_part(db, id) -> StampingPartVO
def list_parts(db, ...) -> PageResult[StampingPartVO]

# ❌ 禁止
def get_part(...) -> dict
```

### 3.3 Router → ApiResponse[T]

```python
# ✅ 正确
return ApiResponse.ok(data=vo)
return ApiResponse.created(data=vo)
return ApiResponse.ok(data=page_result)  # 分页：Service 返回 PageResult，Router 直接透传

# ❌ 禁止
return {"data": vo}  # 直接返回 dict
return vo.model_dump()  # 对 VO 使用 model_dump
return ApiResponse.list_(items=vo_list, total=total, ...)  # 禁止 Router 构造分页
```

---

## 4. 异常体系

### 4.1 异常定义

```python
class AppException(Exception):
    """根异常"""
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code


class BusinessException(AppException):
    """业务异常，4xx"""
    def __init__(self, message: str, code: int = 400):
        super().__init__(message, code=code)


class NotFoundException(BusinessException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code=404)


class PermissionException(BusinessException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, code=403)


class ConflictException(BusinessException):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, code=409)


class SystemException(AppException):
    """系统异常，5xx"""
    def __init__(self, message: str = "系统异常"):
        super().__init__(message, code=500)


class DatabaseException(SystemException):
    def __init__(self, message: str = "数据库错误"):
        super().__init__(message)


class ExternalServiceException(SystemException):
    def __init__(self, message: str = "外部服务调用失败"):
        super().__init__(message)
```

### 4.2 使用规范

```python
# ✅ Service 层抛出异常
def get_part(db, id):
    part = self.repo.get_by_id(db, id)
    if not part:
        raise NotFoundException(f"零件不存在: id={id}")
    return StampingPartVO.model_validate(part)


# ✅ DELETE 正确写法
def delete_part(db, id):
    part = self.repo.get_by_id(db, id)
    if not part:
        raise NotFoundException(f"零件不存在: id={id}")
    self.repo.delete(db, part)
    # 返回 None，由 Router 返回 ApiResponse.deleted()
# ❌ 禁止
raise ValueError("零件不存在")  # 禁止使用 ValueError
return False  # 禁止用 bool 表示失败
```

### 4.3 全局异常处理器

```python
# app/exceptions/handlers.py
# app/exceptions/handlers.py
async def business_exception_handler(request, exc: BusinessException):
    return JSONResponse(
        status_code=exc.code,
        content=ApiResponse.fail(message=exc.message, code=exc.code).model_dump()
    )

async def system_exception_handler(request, exc: SystemException):
    return JSONResponse(
        status_code=500,
        content=ApiResponse.fail(message="系统异常，请稍后重试", code=500).model_dump()
    )

# main.py 注册
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(SystemException, system_exception_handler)

```

---

## 5. 事务管理

**事务必须在 Service 层管理**

```python
# ✅ Service 层
# ✅ 推荐：使用上下文管理器，自动 rollback
def create_order(db, data):
    with db.begin():
        order = self.repo.create(db, data)
        self.inventory_repo.decrease(db, ...)
    return OrderVO.model_validate(order)

# ✅ 也可行：显式 begin/commit/rollback
def create_order(db, data):
    try:
        db.begin()
        self.repo.create(db, data)
        self.inventory_repo.decrease(db, ...)
        db.commit()
    except Exception:
        db.rollback()
        raise BusinessException("创建失败")

# ❌ Repository 禁止 commit/rollback
class OrderRepository:
    def create(self, db, data):
        db.add(Order(**data))
        db.commit()  # 禁止

---

---
## 6. N+1 查询

```python
from sqlalchemy.orm import joinedload, selectinload

# ✅ 预加载关联数据
def list_with_processes(db, ...):
    return db.query(Part).options(
        selectinload(Part.processes)
    ).all()

# ❌ N+1 问题
def list_parts(db, ...):
    parts = db.query(Part).all()
    for p in parts:
        p.processes  # 每次访问触发新查询
    禁止在 VO 序列化阶段触发数据库查询（lazy load 导致 N+1）
```

---

## 7. 序列化规范

### 7.1 Decimal → str（禁止 float）

```python
@field_serializer("thickness", "weight")
def serialize_numbers(self, value):
    if isinstance(value, Decimal):
        return str(value)  # 保留精度
    return value
```

### 7.2 datetime → str

```python
@field_serializer("created_at")
def serialize_datetime(self, value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value
```

---

## 8. 代码审查清单

### 禁止

```
return dict / JSONResponse
Router 返回 ORM Model
VO.model_dump() 用于返回
Repository 返回 dict
raise ValueError
Repository 执行 commit
```

### 必须

```
response_model=ApiResponse[T]
Router 用 ApiResponse.xxx() 返回
Service 返回 VO / PageResult[VO] / None
Repository 返回 SQLAlchemy Model
使用 AppException 体系
Service 层管理事务（推荐 with db.begin()）
使用 joinedload/selectinload
```
