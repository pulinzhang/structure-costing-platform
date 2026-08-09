---
alwaysApply: true
description: FastAPI 后端类型安全、分层架构与 API 契约规范
---

# FastAPI 后端类型安全规范

## 1. API 响应契约

每个 API 接口必须定义 `response_model`：

```python
response_model=ApiResponse[T]
```

示例：

单个对象：
```python
ApiResponse[StampingPartWithProcessesResponse]
```

列表：
```python
ApiResponse[list[StampingProcessResponse]]
```

分页：
```python
ApiResponse[PageResult[StampingPartListResponse]]
```

统计：
```python
ApiResponse[DashboardStatsVO]
```

> **返回值注解**：推荐添加 `-> ApiResponse[T]`，便于类型检查，但 FastAPI 实际运行不强制要求。

---

## 2. ApiResponse 定义规范

### 2.1 响应模型定义

```python
from typing import Generic, TypeVar, Any
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应"""

    code: int = 200  # 状态码：200=成功，400=业务错误，500=系统错误
    success: bool = True
    message: str = "操作成功"
    data: T | None = None

    @classmethod
    def ok(cls, data: T = None, message: str = "操作成功") -> "ApiResponse[T]":
        """成功响应（2xx）"""
        return cls(code=200, success=True, message=message, data=data)

    @classmethod
    def fail(
        cls,
        message: str = "操作失败",
        code: int = 400,
        data: Any = None,
    ) -> "ApiResponse[Any]":
        """业务错误响应（4xx），如参数校验失败、业务规则冲突"""
        return cls(code=code, success=False, message=message, data=data)

    @classmethod
    def error(
        cls,
        message: str = "系统错误",
        code: int = 500,
    ) -> "ApiResponse[None]":
        """系统错误响应（5xx）"""
        return cls(code=code, success=False, message=message, data=None)

    @classmethod
    def created(
        cls,
        data: T,
        message: str = "创建成功",
    ) -> "ApiResponse[T]":
        """创建成功响应"""
        return cls(code=201, success=True, message=message, data=data)

    @classmethod
    def updated(
        cls,
        data: T,
        message: str = "更新成功",
    ) -> "ApiResponse[T]":
        """更新成功响应"""
        return cls(code=200, success=True, message=message, data=data)

    @classmethod
    def deleted(cls, message: str = "删除成功") -> "ApiResponse[None]":
        """删除成功响应"""
        return cls(code=200, success=True, message=message, data=None)
```

### 2.2 方法选择规则

| 场景 | 方法 | code | 说明 |
|------|------|------|------|
| 正常返回（无 data） | `ApiResponse.ok()` | 200 | |
| 正常返回（有 data） | `ApiResponse.ok(data=vo)` | 200 | |
| 创建资源 | `ApiResponse.created(data=vo)` | 201 | |
| 更新资源 | `ApiResponse.updated(data=vo)` | 200 | |
| 删除资源 | `ApiResponse.deleted()` | 200 | |
| 参数校验失败 | `ApiResponse.fail(message=..., code=400)` | 400 | |
| 业务规则冲突 | `ApiResponse.fail(message=..., code=422)` | 422 | |
| 资源不存在 | `HTTPException(status_code=404)` | - | 用 FastAPI 异常，不用 fail() |
| 系统异常 | `ApiResponse.error(message=..., code=500)` | 500 | |

### 2.3 分页组装模式

**必须：Service 组装 PageResult，Router 仅包装**

```python
# ✅ Service：构造 PageResult
def list_parts(self, db, query) -> PageResult[StampingPartListResponse]:
    parts, total = self.repository.paginate(db, ...)
    vo_list = [StampingPartListResponse.model_validate(p) for p in parts]
    total_pages = (total + query.size - 1) // query.size if total > 0 else 0
    return PageResult(
        items=vo_list,
        total=total,
        page=query.page,
        page_size=query.size,
        total_pages=total_pages,
        has_next=query.page < total_pages,
        has_prev=query.page > 1,
        filters=filter_options,
    )

# ✅ Router：仅包装 ApiResponse
@router.get("/parts/list", response_model=ApiResponse[PageResult[StampingPartListResponse]])
def list_parts(...) -> ApiResponse[PageResult[StampingPartListResponse]]:
    return ApiResponse.ok(data=_service.list_parts(db, query))
```

**禁止**：Router 组装 PageResult。

```python
# ❌ 禁止：Router 组装
@router.get("/parts/list")
def list_parts(...):
    data, total, filters = _service.list_parts(db, query)  # Service 返回 tuple
    return ApiResponse.list_(items=data, total=total, ...)  # Router 组装
```

> **为什么禁止 `ApiResponse.list_()`**：`list_()` 方法内部构造 PageResult，导致分页逻辑分散在两处。统一由 Service 构造，便于维护和测试。

### 2.4 方法选择规则

```python
# ❌ 禁止：绕过 Pydantic
return JSONResponse(...)
return {"success": True, "data": ...}

# ❌ 禁止：在错误响应中返回 data（除非是详细错误信息对象）
ApiResponse.fail(message="参数错误", data={"field": "xxx"})  # 仅校验详细错误时允许
```

---

## 3. 分页响应规范

**必须使用公共分页类**：`app/schemas/common/page_result.py` 中的 `PageResult`。

禁止在各 VO 文件中自定义分页结构（如 `XXXListData`）。

### 3.1 PageResult 定义

```python
from typing import Generic, TypeVar, Any, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    """通用分页响应模型"""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False
    filters: Optional[Any] = None  # 类型由调用方保证
```

> **filters 字段**：`filters: Optional[Any]` 而非 `dict | None`，因为实际业务中 filters 可能是强类型 DTO，便于前端动态渲染筛选项。

### 3.2 强制规则

```python
# ❌ 禁止：自定义分页类
class StampingPartListData(BaseModel):
    list: list[StampingPartListResponse]
    total: int
    page: int
    ...

# ✅ 必须：使用公共 PageResult
from app.schemas.common.page_result import PageResult

@router.get("/parts", response_model=ApiResponse[PageResult[Any]])
def list_parts(...) -> ApiResponse[PageResult[Any]]:
    ...
```

### 3.3 分页响应结构

禁止将分页字段直接放入 `ApiResponse`。

禁止：
```json
{
    "code": 200,
    "success": true,
    "message": "查询成功",
    "data": [],
    "total": 100,
    "page": 1,
    "page_size": 20
}
```

必须：
```json
{
    "code": 200,
    "success": true,
    "message": "查询成功",
    "data": {
        "items": [],
        "total": 100,
        "page": 1,
        "page_size": 20,
        "total_pages": 5,
        "has_next": true,
        "has_prev": false,
        "filters": null
    }
}
```

---

## 4. DTO 与 model_dump 规范

### 4.1 职责边界

```python
# DTO：请求输入 → Service → Repository
# model_dump() 仅在此链路中使用

# VO：数据库 → Service → API 输出
# 禁止对 VO 使用 model_dump() 返回
```

### 4.2 允许使用 model_dump() 的场景

```python
# 场景 1：DTO 传给 Repository 更新
def update_part(db, part_id: int, dto: StampingPartUpdateDTO):
    repo.update(db, part_id, dto.model_dump(exclude_unset=True))

# 场景 2：内部数据结构转换
internal_data = SomeModel(...).model_dump()
```

### 4.3 禁止使用 model_dump() 的场景

```python
# ❌ 禁止：VO 用于 API 输出
return ApiResponse.ok(data=vo.model_dump())

# ❌ 禁止：Service 返回 dict
return {"id": vo.id, "name": vo.name}

# ✅ 正确：VO 直接返回
return ApiResponse.ok(data=vo)
```

### 4.4 DTO 更新参数传递

```python
# ✅ 推荐：Service 接收 DTO，用 model_dump() 提取参数
class StampingPartService:
    def update_part(
        self,
        db: Session,
        part_id: int,
        dto: StampingPartUpdateDTO,
    ) -> StampingPartVO:
        update_data = dto.model_dump(exclude_unset=True)
        part = self.repository.update(db, part_id, update_data)
        return StampingPartVO.model_validate(part)

# ✅ 替代：Service 接收 dict（当 DTO 已经是 dict 时）
def update_part(self, db: Session, part_id: int, update_data: dict):
    part = self.repository.update(db, part_id, update_data)
    ...
```

---

## 5. 分层架构规范

项目遵循以下架构：

```
Router（路由层）
   │
   ▼
Service（服务层）
   │
   ▼
Repository（仓库层）
   │
   ▼
Database（数据库）
```

每层有严格的职责划分。

---

## 6. Repository 层规范（Infrastructure）

**Repository 是基础设施层，只负责数据访问**

```
Database
    |
    v
Repository ← 只做数据读写
    |
    | SQLAlchemy Model
    | total
    v
Service ← 业务逻辑
    |
    | VO / PageResult[VO]
    v
Router ← HTTP Facade
    |
    v
ApiResponse[T]
```

Repository 只做：

* SQL 查询
* 数据分页（skip/limit）
* 计数（total）

Repository 必须返回：

* SQLAlchemy Model
* list[SQLAlchemy Model]
* tuple[list[SQLAlchemy Model], int]  # paginate 返回
* Optional[SQLAlchemy Model]

Repository 不知道：

* VO 是什么
* PageResult 是什么
* JSON 结构
* 前端字段

Repository 禁止：

* 创建 API 响应
* 转换为 VO
* 序列化字段
* 格式化 datetime / Decimal
* 处理前端结构

```python
def paginate(
    self,
    db: Session,
    vehicle_model: str,
    skip: int,
    limit: int,
) -> tuple[list[StampingPart], int]:
    """Repository 只返回 SQLAlchemy Model + total，不涉及任何业务逻辑"""
    q = db.query(StampingPart).filter(
        StampingPart.vehicle_model == vehicle_model
    )
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return items, total
```

正确：
```python
def get_by_id(
    self,
    db: Session,
    part_id: int
) -> StampingPart | None:
    return db.query(StampingPart).filter(
        StampingPart.id == part_id
    ).first()
```

错误：
```python
def get_by_id(...):
    return {
        "id": part.id,
        "part_number": part.part_number
    }
```

---

## 7. Service 层规范（Application）

**Service 是应用层，负责业务逻辑和数据转换**

Service 职责：

1. **业务逻辑** - 规则验证、状态检查
2. **权限检查** - 业务层面的权限控制
3. **数据计算** - 价格计算、数量汇总等
4. **ORM → VO 转换** - SQLAlchemy Model 转为 Pydantic VO
5. **分页构造** - 计算 total、total_pages、filters

```
Repository
    |
    | list[Model], total
    v
Service
    |
    | ORM → VO
    | 业务计算
    | 分页计算
    v
VO / PageResult[VO]
    |
    v
Router
```

Service 必须返回：

* `VO`
* `list[VO]`
* `PageResult[VO]`  # 分页场景，必须由 Service 构造

**分页规范**：所有分页方法必须返回 `PageResult[VO]`

```python
def list_parts(
    self,
    db: Session,
    query: StampingPartQuery,
) -> PageResult[StampingPartListResponse]:
    """Service 负责：ORM→VO、计算分页、构造 PageResult"""
    # 1. Repository 返回 Model + total
    parts, total = self.repository.paginate(...)
    # 2. ORM → VO
    vo_list = [StampingPartListResponse.model_validate(p) for p in parts]
    # 3. 分页计算
    total_pages = (total + query.size - 1) // query.size if total > 0 else 0
    # 4. 构造 PageResult
    return PageResult(
        items=vo_list,
        total=total,
        page=query.page,
        page_size=query.size,
        total_pages=total_pages,
        has_next=query.page < total_pages,
        has_prev=query.page > 1,
        filters=self._build_filter_options(db, query),
    )
```

禁止：

```python
dict
dict[str, Any]
model_dump()  # 禁止用于返回
```

示例：

正确：
```python
def get_by_id(
    self,
    db: Session,
    part_id: int
) -> StampingPartWithProcessesResponse | None:
    part = self.repository.get_by_id(db, part_id)
    if not part:
        return None
    return StampingPartWithProcessesResponse.model_validate(part)
```

错误：
```python
return {
    "id": part.id,
    "part_number": part.part_number
}
```

### 7.1 Router 层规范（HTTP Facade）

**Router 是 HTTP 门面层，只负责请求接收和响应包装**

```
HTTP Request
      |
      v
  Router(Facade) ← 只做适配，不做业务
      |
      v
  Service(Application Layer) ← 业务逻辑
      |
      v
 Repository(Infrastructure) ← 数据访问
      |
      v
 Database
```

Router 只负责：

1. 接收 HTTP 请求
2. 参数校验（FastAPI + DTO）
3. 权限 / 依赖注入（Depends）
4. 调用 Service
5. 包装统一响应 `ApiResponse.ok(data=result)`

Router **不知道**：

* `total` 怎么计算
* `page` 怎么计算
* `filters` 怎么生成
* ORM 怎么转换为 VO
* Decimal 怎么格式化

Router 禁止：

* 创建 PageResult
* 计算分页
* 转换 ORM → VO
* 序列化字段
* 组装响应数据结构

```python
@router.get(
    "/parts",
    response_model=ApiResponse[PageResult[StampingPartListResponse]]
)
def list_parts(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
) -> ApiResponse[PageResult[StampingPartListResponse]]:
    """Router 只调用 Service，Service 返回什么就返回什么"""
    return ApiResponse.ok(data=_service.list_parts(db, query))
```

禁止：

```python
# ❌ 禁止：Router 计算分页
data, total = _service.list_parts(db, query)
return ApiResponse.ok(data=PageResult(
    items=data,
    total=total,
    page=query.page,
    ...
))

# ❌ 禁止：Router 转换 VO
part = _repository.get(db, part_id)
return ApiResponse.ok(data=PartVO.model_validate(part))
```

---

## 8.1 HTTP 方法响应规范

每种 HTTP 方法必须遵循一致的响应模式：

| 方法 | 用途 | Service 返回 | Router 返回 | code | Response Model |
|------|------|-------------|-------------|------|----------------|
| `GET`（单个） | 获取单个资源 | `VO` 或 `None` | `ApiResponse.ok(data=vo)` 或 `HTTPException(404)` | 200 / 404 | `ApiResponse[StampingPartVO]` |
| `GET`（列表） | 获取资源列表（不分页） | `list[VO]` | `ApiResponse.ok(data=list)` | 200 | `ApiResponse[list[StampingProcessResponse]]` |
| `GET`（列表） | 获取资源列表（分页） | `PageResult[VO]` | `ApiResponse.ok(data=page_result)` | 200 | `ApiResponse[PageResult[StampingPartVO]]` |
| `POST` | 创建资源 | `VO` | `ApiResponse.created(data=vo)` | 201 | `ApiResponse[StampingPartVO]` |
| `PUT` / `PATCH` | 更新资源 | `VO` 或 `None` | `ApiResponse.updated(data=vo)` 或 `HTTPException(404)` | 200 / 404 | `ApiResponse[StampingProcessResponse]` |
| `DELETE` | 删除资源 | `bool` 或 `None` | `ApiResponse.deleted()` 或 `HTTPException(404)` | 200 / 404 | `ApiResponse[None]` |

### GET - 获取单个资源

```python
@router.get(
    "/parts/{part_id}",
    response_model=ApiResponse[StampingPartWithProcessesResponse]
)
def get_part(
    part_id: int,
    db: Session = Depends(get_db)
) -> ApiResponse[StampingPartWithProcessesResponse]:
    """获取单个零件（包含工序）"""
    part = _stamping_service.get_by_id(db, part_id)
    if not part:
        raise HTTPException(status_code=404, detail="零件不存在")
    return ApiResponse.ok(data=part, message="零件更新成功")
```

### GET - 获取列表（不分页）

```python
@router.get(
    "/processes",
    response_model=ApiResponse[list[StampingProcessResponse]]
)
def list_processes(
    db: Session = Depends(get_db)
) -> ApiResponse[list[StampingProcessResponse]]:
    service = StampingProcessService()
    processes = service.list_processes(db)
    return ApiResponse.ok(data=processes)
```

### GET - 获取列表（分页）

```python
@router.get(
    "/parts/list",
    response_model=ApiResponse[PageResult[StampingPartListResponse]]
)
def list_parts(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
) -> ApiResponse[PageResult[StampingPartListResponse]]:
    """获取零件列表（包含工序）"""
    return ApiResponse.ok(data=_stamping_service.list_parts(db, query))
```

### POST - 创建资源

```python
@router.post(
    "/parts",
    response_model=ApiResponse[StampingPartVO],
    status_code=status.HTTP_201_CREATED
)
def create_part(
    dto: StampingPartCreateDTO,
    db: Session = Depends(get_db)
) -> ApiResponse[StampingPartVO]:
    service = StampingPartService()
    part = service.create_part(db, dto)
    return ApiResponse.created(data=part, message="创建成功")
```

### PUT - 更新资源

```python
@router.put(
    "/parts/{part_id}",
    response_model=ApiResponse[StampingPartVO]
)
def update_part(
    part_id: int,
    dto: StampingPartUpdateDTO,
    db: Session = Depends(get_db)
) -> ApiResponse[StampingPartVO]:
    service = StampingPartService()
    part = service.update_part(db, part_id, dto)
    if not part:
        raise HTTPException(status_code=404, detail="零件不存在")
    return ApiResponse.updated(data=part, message="更新成功")
```

### PATCH - 部分更新资源

```python
@router.patch(
    "/processes/{process_id}",
    response_model=ApiResponse[StampingProcessResponse]
)
def update_process(
    process_id: int,
    body: StampingProcessUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[StampingProcessResponse]:
    """更新工序（如成本系数）"""
    result = _stamping_service.update_process(
        db, process_id, body.model_dump(exclude_unset=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="工序不存在")
    return ApiResponse.ok(data=result, message="工序更新成功")
```

### DELETE - 删除资源

```python
@router.delete(
    "/parts/{part_id}",
    response_model=ApiResponse[None]
)
def delete_part(
    part_id: int,
    db: Session = Depends(get_db)
) -> ApiResponse[None]:
    """删除零件（同时删除关联工序）"""
    success = _stamping_service.delete(db, part_id)
    if not success:
        raise HTTPException(status_code=404, detail="零件不存在")
    return ApiResponse.deleted(message="零件删除成功")
```

### 错误响应模式

所有接口应一致地处理错误：

```python
from fastapi import HTTPException, status

@router.get("/parts/{part_id}", ...)
def get_part(...):
    try:
        part = _stamping_service.get_by_id(db, part_id)
        if not part:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="零件不存在")
        return ApiResponse.ok(data=part)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
```

注意：
- 使用 `HTTPException` 处理错误
- `detail` 会通过 FastAPI 异常处理器包含在响应的 `message` 字段中
- 业务校验失败用 `ApiResponse.fail(code=422, message="...")`
- 系统异常用 `ApiResponse.error(code=500, message="...")`

---

## 9. VO 规范

VO 仅用于 API 输出。

每个 VO 必须支持 ORM 转换。

必须：
```python
class StampingPartListResponse(BaseModel):

    model_config = {
        "from_attributes": True
    }
```

VO 负责：

* API 字段定义
* 输出命名
* 数据格式化
* 序列化

VO 禁止包含：

* 数据库操作
* 业务逻辑
* SQL 查询

---

## 10. ORM 到 VO 转换规范

SQLAlchemy Model：
```python
StampingPart
```

必须使用以下方式转换：

```python
StampingPartListResponse.model_validate(
    stamping_part
)
```

必须：
```python
model_config = {
    "from_attributes": True
}
```

禁止：
```python
StampingPartListResponse(
    **stamping_part.__dict__
)
```

禁止：
```python
dict(stamping_part)
```

---

## 11. 序列化规范

所有特殊类型转换必须在 VO 内部完成。

禁止在以下层序列化：

* Router
* Service
* Repository

---

### Decimal 序列化

使用：
```python
@field_serializer
```

示例：
```python
@field_serializer("thickness", "part_weight")
def serialize_decimal(self, value):
    if isinstance(value, Decimal):
        return float(value)
    return value
```

---

### datetime 序列化

使用：
```python
@field_serializer
```

示例：
```python
@field_serializer("created_at", "updated_at")
def serialize_datetime(self, value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value
```

---

### Enum 序列化

使用：
```python
@field_serializer
```

禁止在 Router 或 Service 中手动转换 Enum 值。

---

## 12. API 数据流

必须的数据流：

```
Database
   │
   ▼
SQLAlchemy Model
   │
   ▼
Service
   │
   ▼
Pydantic VO
   │
   ▼
ApiResponse[T]
   │
   ▼
FastAPI JSON Response
```

禁止：

```
Database
   │
   ▼
dict
   │
   ▼
Router
   │
   ▼
JSON
```

---

## 13. 重构规范

修改现有代码时：

1. 不要一次性重构整个项目
2. 一次只修改一个模块
3. 保持现有的 JSON 结构不变
4. 改实现前先添加 response_model
5. 每个模块后运行类型检查

推荐顺序：

```
1. app/utils/response.py（ApiResponse 和 PageResult）

2. app/schemas/vo（VO 定义）

3. app/services（Service 层）

4. app/routers（Router 层）
```

---

## 14. 代码审查清单

提交前检查：

禁止：
```
return dict
return JSONResponse
return ORM Model from Router
model_dump() 用于 VO 返回
VO.model_dump() for API output
__dict__
dict(model)
ApiResponse[Any]（应指定具体类型）
```

必须：
```
每个接口：
    response_model=ApiResponse[T]

每个 Router：
    使用 ApiResponse.xxx() 方法返回

每个 Service：
    returns VO 或 PageResult

每个 Repository：
    returns SQLAlchemy Model

分页接口：
    Service 返回 PageResult[VO]
    Router 用 ApiResponse.ok(data=page_result) 包装
```
