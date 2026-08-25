---
description: FastAPI 后端类型安全、分层架构、API 契约、权限拦截与 Any 函数边界
---

# FastAPI 后端类型安全规范

> **实现真相**：`app/utils/response.py`、`app/schemas/common/page_result.py`。  
> **Cursor 规则**：`.cursor/rules/api-type-safety.mdc`（与本文应对齐；改一处须改两处）。  
> 分层与切片依赖见 [`architecture.md`](./architecture.md) / [`architecture-constitution.mdc`](./architecture-constitution.mdc)。  
> 权限目录 / 新增功能清单见 [`permission-design.md`](./permission-design.md)。

## 1. API 响应契约

JSON 业务接口必须同时定义：

```python
response_model=ApiResponse[T]
```

以及匹配的返回注解：

```python
-> ApiResponse[T]
```

**例外（现网已落地）**：Excel / 原件下载返回 `StreamingResponse` 或 `FileResponse`，不要套 `ApiResponse`，也不要 `response_model=ApiResponse[…]`。禁止业务 Router 返回裸 dict / 裸 `JSONResponse`。全局异常 handler 可用 `JSONResponse` 包 `ApiResponse.fail().model_dump()`。

示例：

单个对象：
```python
ApiResponse[StampingPartWithProcessesResponse]
```

列表（不分页）：
```python
ApiResponse[list[StampingProcessResponse]]
```

分页（**只用** `PageResult`；`BasePageResponse` 为其别名，新代码写 `PageResult`）：
```python
ApiResponse[PageResult[StampingPartListResponse]]
```

统计：
```python
ApiResponse[DashboardStatsVO]
```

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

    @classmethod
    def list_(
        cls,
        items: list[Any],
        total: int,
        page: int = 1,
        page_size: int = 20,
        message: str = "查询成功",
        filters: Any = None,
    ) -> "ApiResponse[Any]":
        """分页列表：内部构造 PageResult 放入 data（实现见 app/utils/response.py）"""
        ...
```

### 2.2 方法选择规则

| 场景 | 方法 | code | 说明 |
|------|------|------|------|
| 正常返回（无 data） | `ApiResponse.ok()` | 200 | |
| 正常返回（有 data） | `ApiResponse.ok(data=vo)` | 200 | |
| **分页列表** | **`ApiResponse.list_(items=..., total=..., page=..., page_size=..., filters=...)`** | 200 | data 为 `PageResult` |
| 创建资源（CRUD / 同步导入已有结果 VO） | `ApiResponse.created(data=vo)` | 201 | |
| **`start_*` 立即返回 `task_id`** | **`ApiResponse.ok(data=accepted)`** | **200** | 不要套 POST=201 |
| 更新资源（PUT/PATCH） | `ApiResponse.updated(data=vo)` | 200 | 批量审核/删除用 `ok(data=result)` |
| 删除资源 | `ApiResponse.deleted()` | 200 | |
| Excel / 原件下载 | `StreamingResponse` / `FileResponse` | — | 不走 `ApiResponse` |
| 参数校验失败 | 请求体 Pydantic → `validation_exception_handler` | 422 | Router 不要手写 fail() |
| 业务拒绝 | Service `raise BusinessException` | 400 | 唯一键/审核锁/缺字段；禁止 `(None, msg)` |
| 期别/范围冲突 | Service `raise BusinessException(..., code=409)` | 409 | 重复计算锁；不要 Router 转 `HTTP_409` |
| 资源不存在 | Service `raise NotFoundException` | 404 | 含任务过期；Router 不要 `if not vo: 404` |
| 未登录 | 依赖 `HTTPException(401)` | 401 | 仅 `deps/auth`，不是切片 Service |
| 系统异常 | 未捕获 Exception → `generic_exception_handler` | 500 | 禁止 `BusinessException(str(exc))` / `return None, str(exc)` |

### 2.3 分页组装模式（现网约定）

**推荐（与现有 Router 一致）**：Service 返回 VO 列表 + total（+ 可选 filters），Router 用 `ApiResponse.list_()` 组装 `PageResult`。

```python
# ✅ Service：ORM→VO，返回列表与总数（及筛选元数据）
def paginate(
    self, db: Session, query: SteelPriceQuery,
) -> tuple[list[SteelPriceResponse], int, FilterOptionsVO]:
    rows, total = self.repository.paginate(db, ...)
    vos = [SteelPriceResponse.model_validate(r) for r in rows]
    return vos, total, self._filter_options(db, query)

# ✅ Router：list_() 计算 total_pages / has_next / has_prev 并包进 data
@router.get("", response_model=ApiResponse[PageResult[SteelPriceResponse]])
def list_steel_prices(
    query: SteelPriceQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_LIST_VIEW)),
) -> ApiResponse[PageResult[SteelPriceResponse]]:
    records, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,  # 优先直接传 filters VO，不要为 list_ 再 model_dump
    )
```

**亦允许**：Service 自行构造完整 `PageResult[VO]`，Router 用 `ApiResponse.ok(data=page_result)`。两种勿在同一接口混用。

```python
# ✅ 备选：Service 返回 PageResult
return ApiResponse.ok(data=_service.list_as_page(db, query))
```

**禁止**：

```python
# ❌ 把 total/page 摊在 ApiResponse 根上
return {"success": True, "data": [], "total": 100}

# ❌ 不用 list_/PageResult，手写裸 dict 当 data
return ApiResponse.ok(data={"items": ..., "total": ...})
```

> `ApiResponse.list_()` **允许且推荐**用于分页。旧文档曾禁止 `list_()`，已与实现不符，作废。

### 2.4 禁止绕过契约

```python
# ❌ 禁止：业务 Router 绕过 Pydantic / ApiResponse
return JSONResponse(...)
return {"success": True, "data": ...}

# ❌ 禁止：Router 手写 ApiResponse.fail()（业务失败由 Service 抛异常，全局 handler 写 fail）
```

`fail()` 的 `data` **仅**全局 `validation_exception_handler` 用来带字段错误列表。业务 handler 不带 `data`。业务 Router 不要自己调 `fail()`。

全局 handler 用 `JSONResponse(content=ApiResponse.fail(...).model_dump())` 是实现例外，不算「业务 Router 返回 JSONResponse」。

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

# ✅ 必须：使用公共 PageResult（新代码优先此名；BasePageResponse 仅为别名）
from app.schemas.common.page_result import PageResult

@router.get("/parts", response_model=ApiResponse[PageResult[StampingPartListResponse]])
def list_parts(...) -> ApiResponse[PageResult[StampingPartListResponse]]:
    ...
```

列表 **HTTP 查询参数必须是 `page` + `size`**（`page` 从 1 起）。禁止 Router / DTO 再暴露 `skip` / `limit`。Repository 内部可用 `skip` / `limit` 表示 SQL `OFFSET` / `LIMIT`，由 Service 换算。

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
# 禁止对 VO 使用 model_dump() 作为 API 返回值
# 允许：切片 Service 把 VO dump 进异步任务 result_json（持久化，见架构宪法 §5.3）
```

### 4.2 允许使用 model_dump() 的场景

```python
# 场景 1：DTO 传给 Repository 更新
def update_part(db, part_id: int, dto: StampingPartUpdateDTO):
    repo.update(db, part_id, dto.model_dump(exclude_unset=True))

# 场景 2：内部数据结构转换
internal_data = SomeModel(...).model_dump()

# 场景 3：异步任务 result 写入辅助库 JSON（非 API 输出）
result=result_vo.model_dump()  # WorkerTaskOutcome；Router 禁止 dump
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
# ✅ 推荐：Service 接收 DTO，原样或按列交给 Repository
class StampingPartService:
    def update_part(
        self,
        db: Session,
        part_id: int,
        dto: StampingPartUpdateDTO,
        current_user: UserVO,
    ) -> StampingPartVO:
        part = self.repository.update(db, part_id, dto, current_user=current_user)
        return StampingPartVO.model_validate(part)
```

写入 Repository 用 DTO / dataclass / `TypedDict`，不要把 Service 签名收成 `dict`。

---

## 5. 分层架构规范

项目遵循：

```
Router → Service → Repository → Database
```

Parser 仅由 Service 调用。切片依赖为**有向无环**（下游 costing/dashboard 可组合上游），详见架构宪法。

每层职责划分见架构说明；本节只约束**类型与返回形态**。

### 5.1 `Any`：适度禁用（核心：不跨越函数边界）

**原则**：不把 `Any` 写进函数的参数或返回值。签名一旦是 `Any`，调用链上的类型检查全部失效。

这是**适度**禁用，不是项目里消灭每一个 `Any`：函数体内可以暂时接住无类型的第三方结果，但**走出这个函数之前必须收成具体类型**。

| 位置 | 允许 | 禁止 |
|------|------|------|
| **函数签名**（含方法、模块级函数） | DTO / dataclass / `TypedDict` / Model / VO / `TypeVar` / 标准库类型 | `Any`、`dict[str, Any]`、`list[Any]`、`**kwargs: Any`、`Callable[..., Any]` 当业务 API |
| **函数体内** | `json.loads`、无 stub 的第三方对象；立刻收窄后再往下传 | 把未收窄的 `Any` 传给其它函数 |
| **Repository 写入** | 整行新建用 dataclass；部分更新用 `TypedDict, total=False`；字段已对齐时也可直接收 HTTP DTO | `{**dto.model_dump(), **audit_create()}` 当作参数类型；VO 进入 Repository |
| **聚合 / 筛选** | 具名 `TypedDict` 或 Pydantic 模型 | `dict[str, Any]` 当 `filters` / `summary` |

替代优先级：

1. HTTP 入参 → `app/schemas/dto/` 的 DTO  
2. HTTP 出参 → VO（**只** Service → Router，不进 Repository）  
3. Service → Repository 整行写入 → `@dataclass`（含审计字段，按列对齐）  
4. 部分更新 → `TypedDict, total=False`（`updated_by=` 显式赋值；不要 `**audit_update()` 打进更窄的 TypedDict）  
5. 真正跨切片复用且无自然归属 → 再抽到 `common/` 或 `persist` 辅助

例外（边界仍须收窄）：

- 框架出口：`ApiResponse.fail` / `ApiResponse.list_` / `PageResult.filters` 的内部泛型可以是 `Any`；**业务 Router** 仍须 `response_model=ApiResponse[具体VO]` 或 `ApiResponse[PageResult[具体VO]]`
- 无类型桩的第三方（如 openpyxl worksheet）：包在小函数里，对外签名不用 `Any`
- `json.loads`：在函数内解析，返回已声明的 VO / TypedDict / 标准类型

不要因为「方便」把 `dict[str, Any]` 留在 Repository / Service / Router 签名上。

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
* 数据分页（SQL `OFFSET` / `LIMIT`；由 Service 从 HTTP `page` / `size` 换算）
* 计数（total）

Repository 必须返回：

* SQLAlchemy Model
* `list[SQLAlchemy Model]`
* `tuple[list[SQLAlchemy Model], int]`（paginate）
* `Optional[SQLAlchemy Model]`
* **允许**：SQL 聚合/去重的具名 `TypedDict`、命名元组或轻量 read-model（如 `summarize_*`、`get_filter_options`）——见架构宪法 Repository 边界；禁止 `dict[str, Any]`
* **写入入参**：dataclass / `TypedDict` / 列对齐的 DTO；禁止 `Any`、禁止 VO

Repository 不知道：

* VO / `PageResult` / API JSON 结构
* 前端字段命名

Repository 禁止：

* 创建 `ApiResponse`
* 转换为 VO
* 格式化 datetime / Decimal 给前端
* 权限/角色业务策略判断

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
5. **分页数据准备** - 查询 total、准备 filters；**推荐**返回 `(list[VO], total[, filters])`，由 Router `list_()` 组装 `PageResult`

```
Repository
    |
    | list[Model], total
    v
Service
    |
    | ORM → VO
    | 业务计算
    v
list[VO], total[, filters]   或   PageResult[VO]（备选）
    |
    v
Router → ApiResponse.list_(...) 或 ApiResponse.ok(data=page)
```

Service 必须返回：

* `VO`
* `list[VO]`
* `tuple[list[VO], int]` / `tuple[list[VO], int, Filters]`  # **推荐分页形态**
* `PageResult[VO]`  # 备选：Service 自行组装分页体
* 调 Repository 时传入具体写入类型（dataclass / TypedDict / DTO），不要 `dict[str, Any]`，不要把 VO 传进 Repository

对 **Router 调用的** 单资源 get / 写操作：找不到或业务拒绝时 **抛异常**（`NotFoundException` / `BusinessException`，冲突用 `code=409`），不要 `VO | None`，不要 `delete → bool`，不要 `tuple[VO | None, str | None]`。细则见架构宪法 §5.2。

**分页推荐写法**：

```python
def paginate(
    self,
    db: Session,
    query: StampingPartQuery,
) -> tuple[list[StampingPartListResponse], int, PartFilterVO]:
    """Service：ORM→VO；Router 再 list_()"""
    parts, total = self.repository.paginate(...)
    vo_list = [StampingPartListResponse.model_validate(p) for p in parts]
    return vo_list, total, self._build_filter_options(db, query)
```

禁止：

```python
dict
dict[str, Any]
model_dump()  # 禁止用于 API 返回
tuple[VO | None, str | None]  # HTTP 错误通道；分页 (list, total) 除外
```

示例：

正确：
```python
def get_by_id(
    self,
    db: Session,
    part_id: int
) -> StampingPartWithProcessesResponse:
    part = self.repository.get_by_id(db, part_id)
    if not part:
        raise NotFoundException(f"零件不存在: id={part_id}")
    return StampingPartWithProcessesResponse.model_validate(part)
```

错误：
```python
return {
    "id": part.id,
    "part_number": part.part_number
}

return None, "零件不存在"
```

---

## 7.0 路由鉴权与权限

> **权限细则唯一真相**：[`permission-design.md`](./permission-design.md)（§0 / §10）。  
> 本节只列类型安全硬约束，不重复权限树与长示例。

| 场景 | 要求 |
|------|------|
| `login` | 不注入 `current_user` |
| `me` / `touch` / `logout` | `Depends(get_current_user)` |
| **其它业务路由** | `Depends(require_perm(Perm.XXX))` / `require_any_perm` / `require_admin_user` |
| 权限码 | 只用 `Perm.*`，禁止 `"op:…"` 字面量 |
| 写操作 | `current_user=` 传给 Service；禁止 ContextVar |
| 前端同码 | `canAccessPage` / `can('op:…')`；不能只藏 UI |
| 失败 | `PermissionException` → HTTP 403 |

```python
from app.common.permissions.codes import Perm
from app.deps.permissions import require_perm

current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW))
```

---

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
5. 包装统一响应：`ApiResponse.ok` / `created` / `updated` / `deleted` / **`list_`（分页）**

Router **不知道**：

* ORM 怎么查
* Decimal / datetime 怎么格式化（在 VO 内）
* 业务规则（通过/驳回等）

Router **可以**：

* 调用 `ApiResponse.list_(items, total, page, page_size, filters=...)` 组装分页壳
* 将 `page` / `page_size` 从 Query/DTO 传入 `list_`（纯 HTTP 适配）

Router 禁止：

* 访问数据库 / 操作 ORM Model
* 在 Router 内 `Model → VO`
* 返回裸 dict；业务 Router 返回裸 `JSONResponse`（下载用 `StreamingResponse` / `FileResponse`；全局 handler 除外）
* 把 Service 错误元组 / `None` 转成 `HTTPException`（见架构宪法 §5.2）

```python
@router.get(
    "/parts",
    response_model=ApiResponse[PageResult[StampingPartListResponse]]
)
def list_parts(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW)),
) -> ApiResponse[PageResult[StampingPartListResponse]]:
    records, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
    )
```

禁止：

```python
# ❌ Router 转换 VO
part = _repository.get(db, part_id)
return ApiResponse.ok(data=PartVO.model_validate(part))

# ❌ 绕过 ApiResponse
return {"items": ..., "total": total}
```

---

## 8.1 HTTP 方法响应规范

每种 HTTP 方法必须遵循一致的响应模式：

| 方法 | 用途 | Service 返回 | Router 返回 | code | Response Model |
|------|------|-------------|-------------|------|----------------|
| `GET`（单个） | 获取单个资源 | `VO`（不存在抛 `NotFoundException`） | `ApiResponse.ok(data=vo)` | 200 / 404 | `ApiResponse[StampingPartVO]` |
| `GET`（列表） | 获取资源列表（不分页） | `list[VO]` | `ApiResponse.ok(data=list)` | 200 | `ApiResponse[list[StampingProcessResponse]]` |
| `GET`（列表） | 获取资源列表（分页） | `list[VO], total[, filters]` 或 `PageResult[VO]` | **`ApiResponse.list_(...)`** 或 `ok(data=page)` | 200 | `ApiResponse[PageResult[…]]` |
| `POST` | 创建资源 | `VO` | `ApiResponse.created(data=vo)` | 201 | `ApiResponse[StampingPartVO]` |
| `POST` | `start_*` 入队（立刻 `task_id`） | `AsyncTaskAcceptedVO` | **`ApiResponse.ok(data=accepted)`** | **200** | `ApiResponse[AsyncTaskAcceptedVO]` |
| `PUT` / `PATCH` | 更新资源 | `VO`（不存在抛 `NotFoundException`） | `ApiResponse.updated(data=vo)` | 200 / 404 | `ApiResponse[StampingProcessResponse]` |
| `POST` | 批量审核 / 批量删除 | 结果 VO | `ApiResponse.ok(data=result)` | 200 | `ApiResponse[…ResultVO]` |
| `DELETE` | 删除资源 | `None`（不存在抛 `NotFoundException`） | `ApiResponse.deleted()` | 200 / 404 | `ApiResponse[None]` |
| `GET` | Excel / 原件下载 | bytes + 文件名 | `StreamingResponse` / `FileResponse` | 200 | 无 `ApiResponse` |

### GET - 获取单个资源

```python
@router.get(
    "/parts/{part_id}",
    response_model=ApiResponse[StampingPartWithProcessesResponse]
)
def get_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW)),
) -> ApiResponse[StampingPartWithProcessesResponse]:
    """获取单个零件（包含工序）"""
    part = _stamping_service.get_by_id(db, part_id)
    return ApiResponse.ok(data=part, message="获取成功")
```

### GET - 获取列表（不分页）

```python
@router.get(
    "/processes",
    response_model=ApiResponse[list[StampingProcessResponse]]
)
def list_processes(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW)),
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
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW)),
) -> ApiResponse[PageResult[StampingPartListResponse]]:
    records, total, filters = _stamping_service.paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
    )
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
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_UPDATE)),
) -> ApiResponse[StampingPartVO]:
    service = StampingPartService()
    part = service.create_part(db, dto, current_user=current_user)
    return ApiResponse.created(data=part, message="创建成功")
```

### POST - 异步入队（`start_*`，HTTP 200）

```python
@router.post("/", response_model=ApiResponse[AsyncTaskAcceptedVO])
async def upload_stamping_file(
    ...,
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    accepted = service.start_upload(..., current_user=current_user)
    return ApiResponse.ok(data=accepted, message="上传成功，后台开始解析")
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
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_UPDATE)),
) -> ApiResponse[StampingPartVO]:
    service = StampingPartService()
    part = service.update_part(db, part_id, dto, current_user=current_user)
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
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_UPDATE)),
) -> ApiResponse[StampingProcessResponse]:
    """更新工序（如成本系数）"""
    result = _stamping_service.update_process(
        db, process_id, body, current_user=current_user
    )
    return ApiResponse.updated(data=result, message="工序更新成功")
```

### DELETE - 删除资源

```python
@router.delete(
    "/parts/{part_id}",
    response_model=ApiResponse[None]
)
def delete_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_DELETE)),
) -> ApiResponse[None]:
    """删除零件（同时删除关联工序）"""
    _stamping_service.delete(db, part_id)
    return ApiResponse.deleted(message="零件删除成功")
```

### 错误响应模式

业务失败由 Service 抛 `NotFoundException` / `BusinessException`（冲突 `code=409`），`business_exception_handler` 写成 `ApiResponse.fail`。Router **不要** `try/except` 再转 `HTTPException`，不要拆 `(record, error)`，不要 `if not vo: 404`。

```python
@router.get("/parts/{part_id}", ...)
def get_part(...):
    part = _stamping_service.get_by_id(db, part_id)
    return ApiResponse.ok(data=part)
```

请求体 Pydantic 校验走 `validation_exception_handler`（422）。未登录走 `deps/auth` 的 `HTTPException(401)`。未捕获异常走 `generic_exception_handler`（500）。细则见架构宪法 §5.2。

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

datetime / Decimal / Enum 的 **JSON 形态**必须在 VO 的 `@field_serializer` 内完成。

禁止在 Router / Service / Repository **手写**这类格式化（如 `strftime`、`float(price)`）。

Service **应当**做 ORM → VO（`model_validate`）；这不是「在 Service 里序列化 JSON」。

---

### Decimal 序列化

#### 金额 / 单价 / 费用 / 费率

这些字段是**精确十进制量**，禁止把 `float` 当作业务类型（DTO / VO / Service / Model / 计算中间态）。

| 层 | 要求 |
|----|------|
| Model | `Numeric(p, s)` + `Mapped[Decimal]` |
| DTO | 字段类型 `Decimal`；`mode="before"` 用 `Decimal(str(value))` 再 `quantize`（JSON number 可能先变成 float，必须立刻经 `str` 转回） |
| Service / Parser / 计算 | 只用 `Decimal` 运算与量化；禁止 `float(x)` 参与金额计算 |
| VO | 字段类型 `Decimal`；`@field_serializer` **输出固定小数位的字符串**（如 `"0.0999"`），禁止序列化为 JSON number / `float` |
| Excel 导入导出 | 单元格读写保持 `Decimal`，不要 `round(float(...))` |

允许（金额类）：
```python
from decimal import Decimal, ROUND_HALF_UP

_UNIT_PRICE_QUANT = Decimal("0.0001")


def quantize_unit_price(value: object) -> Decimal:
    number = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    if number < 0:
        raise ValueError("单价不能为负")
    return number.quantize(_UNIT_PRICE_QUANT, rounding=ROUND_HALF_UP)


class PriceCreateDTO(BaseModel):
    unit_price: Decimal = Field(..., ge=0)

    @field_validator("unit_price", mode="before")
    @classmethod
    def _coerce(cls, value: object) -> Decimal:
        return quantize_unit_price(value)


class PriceVO(BaseModel):
    unit_price: Decimal

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Decimal) -> str:
        quantized = value.quantize(_UNIT_PRICE_QUANT, rounding=ROUND_HALF_UP)
        return f"{quantized:.4f}"
```

禁止（金额类）：
```python
unit_price: float
return float(value)            # VO 序列化
price = float(row.unit_price)  # Service / 计算
round(float(value), 4)         # 导出
```

> JSON 没有 Decimal 类型：传输用**字符串**（推荐，单价/金额），或 JSON number 进入后立刻 `Decimal(str(...))`。业务层长期持有的类型必须是 `Decimal`。

#### 非金额 Decimal（料厚、重量等物理量）

Model / DTO / VO 仍用 `Decimal`。JSON **同样输出固定小数位字符串**（现网走 `format_money` / `optional_format_money`），不要 `float(value)`。

```python
from app.common.money import Q4, optional_format_money

@field_serializer("thickness", "part_weight")
def serialize_physical_decimal(self, value: Decimal | None) -> str | None:
    return optional_format_money(value, Q4, 4)
```

---

### datetime 序列化

使用：
```python
@field_serializer
```

示例：
```python
from app.common.timezone import datetime_to_iso

@field_serializer("created_at", "updated_at")
def serialize_datetime(self, value: datetime | None) -> str | None:
    return datetime_to_iso(value)
```

VO 的 datetime JSON **必须**走 `app.common.timezone.datetime_to_iso`（`isoformat()`，如 `"2026-08-25T10:42:00"`）。禁止各 VO 自写 `strftime("%Y-%m-%d %H:%M:%S")` 或重复的本地 helper。Excel 文件名、归档目录时间戳可以用 `strftime`，那不是 API 输出。

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
return JSONResponse          # 业务 Router；全局 handler 除外
return ORM Model from Router
model_dump() 用于 VO 返回
VO.model_dump() for API output
tuple[VO | None, str | None] 作为 HTTP 错误通道
__dict__
dict(model)
ApiResponse[Any]（应指定具体类型；框架 list_/fail 除外）
业务函数签名使用 Any / dict[str, Any] / list[Any]（须换成 DTO / dataclass / TypedDict / Model）
金额/单价/费用/物理量用 float（须 Decimal；JSON 用字符串）
```

必须：
```
每个接口：
    JSON 业务：response_model=ApiResponse[T]
    下载/导出：StreamingResponse / FileResponse（例外）

每个业务 Router（登录除外）：
    Depends(require_perm(Perm.XXX)) / require_any_perm / require_admin_user
    禁止裸 get_current_user（me/touch/logout 除外）
    禁止权限码字面量，用 Perm.*
    禁止 if error: HTTPException / if not vo: 404 / except 业务失败再转 409

写操作 Router → Service：
    pass current_user=current_user

每个 Router：
    JSON 用 ApiResponse.xxx()；下载不走 ApiResponse

每个 Service：
    returns VO / list[VO] / (list, total[, filters]) / PageResult
    对 Router 入口的失败抛 NotFoundException / BusinessException（冲突 code=409）
    无隐式 current_user / ContextVar

每个 Repository：
    returns SQLAlchemy Model（聚合接口可返回 TypedDict / 轻量结构，禁止匿名 dict）

分页接口：
    推荐 Service 返回 list[VO] + total；Router 用 ApiResponse.list_()
    response_model=ApiResponse[PageResult[VO]]（勿再发明 XXXListData）

前端（同权限码双向）：
    菜单 canAccessPage / applySidebarPermissions
    按钮 can('op:…')
    细则见 docs/permission-design.md
```
