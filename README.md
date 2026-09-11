# 汽车冲压件自动核价平台

> FastAPI + SQLite + 原生 SPA。覆盖冲压工艺、一事一议钢价政策、BOM、钢材联动与零件核价、权限与审计。

**设计风格**：Brabus Carbon & Precision Dark（碳素黑 · 钛灰面板 · 标志性红）

---

## 功能一览

| 模块 | 能力 |
|------|------|
| **登录 / 权限** | 独立登录页；用户、角色权限码；侧栏与接口双向鉴权 |
| **仪表盘** | 管理者看板：本期产出 / 待办与风险 / 核价闭环就绪 + 决策入口 |
| **冲压工程** | 工艺 Excel 上传与解析；零件/工序列表；冲次单价；加工费计算与列表 |
| **一事一议** | 加减价政策上传/列表/匹配；基准价格；中标钢厂厚度一览；废料月度销售价 |
| **焊接工程（BOM）** | 材料清单上传 / 产品结构 / 结构图；焊接单价；年度零件价；包装运输费；焊接工艺拆解；焊接费 |
| **核价** | 冲压钢材联动；零件价格；总成核价；自动核价引擎；月度核对合册 |
| **文件溯源** | 已落盘业务 Excel 登记、筛选、鉴权下载 |
| **AI 助理** | 核价结果智能分析：自然语言提问 → 系统算数 + LLM 解释；Markdown 回答、分析历史、打印/Word 导出 |
| **设置** | 个人资料、系统配置、用户管理、操作日志 |

典型链路：工艺 / 政策 / 基价 / 废料价 / BOM 入库 → 钢材联动 → 零件核价（材料 + 加工费）→ 总成核价 → **AI 助理解读趋势与动因**。

**AI 助理（LLM）**：数字由核价库与 Analysis 层计算，LLM 只负责自然语言解释；问什么答什么，不流式、不跳页。设计详见 [docs/llm/llm-costing-analysis-report-design.md](docs/llm/llm-costing-analysis-report-design.md)。

**生产环境（Windows，可无 Python）**：见 [docs/deploy-windows-production.md](docs/deploy-windows-production.md)，一键脚本 `scripts\windows\setup.bat`。

**云主机 Docker 手工发版**：clone 后配置 `.env`，在仓库根目录执行 `bash deploy.sh`（拉代码、构建镜像、启动容器）。

---

## 架构

**前后端分离 · 垂直切片 · 分层调用**

| 层 | 说明 |
|----|------|
| 后端 | FastAPI，`/api/*` JSON；`ApiResponse[T]` + `PageResult` |
| 前端 | `static/` SPA（无 Webpack/Vite）：Hash 路由、本地 `tailwind.css`、ES Module |
| 分层 | Router → Service → Repository → DB；Parser 仅 Service 调用 |
| 切片 | 上游 `stamping` / `yishiyiyi` / `bom` / `settings`；横切 `file_trace`；下游 `costing` / `dashboard` 可组合上游 |

可读导读：[docs/architecture.md](docs/architecture.md)

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端 | FastAPI、Uvicorn、SQLAlchemy 2、Pydantic v2 |
| 数据库 | SQLite（主库 `data/stamping_costing.db` + 辅助库 `data/auxiliary.db` 会话/异步任务） |
| Excel | OpenPyXL、xlrd；Pillow（简图） |
| 前端 | 原生 JS SPA、本地 Tailwind CSS、Inter + JetBrains Mono |
| 鉴权 | Token（`X-Token` / Bearer）+ `Perm.*` 权限码 |

---

## 快速开始

### 1. 环境要求（PyCharm）

| 项 | 要求 |
|----|------|
| Python | **≥ 3.12**（见 `pyproject.toml` `requires-python`） |
| IDE | **PyCharm**（推荐用项目内 `.venv` 作为解释器） |
| OS | 开发机以 **Windows** 为主；Linux/macOS 亦可 |
| 包管理 | **pip**（本仓库默认路径；不必安装 `uv`） |

**关于 `uv`**：是 Astral 出的另一套高速包管理/运行工具（类似加强版 pip）。本项目的 pre-commit 曾写过 `uv run mypy`，**用 PyCharm 的同学可以完全忽略 `uv`**；钩子已改为 `python -m mypy`，走当前虚拟环境即可。

#### PyCharm 建议设置

1. **File → Settings → Project → Python Interpreter**  
   - 选「Add Interpreter → Virtualenv」  
   - Location：项目下 `.venv`  
   - Base：本机 Python 3.12+  
2. 打开 PyCharm 底部 **Terminal**（已自动激活 `.venv`）再执行下文的 `pip` / `ruff` / `mypy`  
3. **Run/Debug**：可新建配置  
   - Module：`uvicorn`  
   - Parameters：`main:app --reload --host 0.0.0.0 --port 8000`  
   - Working directory：项目根目录  
   或直接跑 `main.py`  

命令行创建 venv（可选，与 PyCharm 二选一即可）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

说明：

- `requirements.txt`：运行时依赖  
- `requirements-dev.txt`：**ruff**、**mypy**、**pre-commit** 及部分 types stubs  
- 也可：`pip install -e ".[dev]"`（若本地以可编辑方式安装本项目）

配置可复制示例后按需修改：

```bash
copy .env.example .env
```

（Linux/macOS：`cp .env.example .env`）

### 2.1 安装 Git 钩子（pre-commit，请务必执行）

> **为什么要拴死？**  
> Python 默认太自由：无注解也能跑、`Any` 到处飞、风格各写各的——问题往往拖到运行时才爆。  
> **`Any` 不得出现在函数参数/返回值上**（函数体内可暂时接住第三方无类型结果，走出函数前必须收窄）——见 [API 类型安全 §5.1](docs/api-type-safety.md)。  
> 本仓库用 **Ruff（风格/低级错误）+ Mypy `strict`（类型契约）+ pre-commit（提交门禁）** 把自由度压住：  
> **过不了检查的代码，不许进 Git。** 这是刻意设计，不是可选装饰。

仓库根目录有 [`.pre-commit-config.yaml`](.pre-commit-config.yaml)。**克隆仓库并装好开发依赖后，请在项目根目录执行一次：**

```bash
pre-commit install
```

作用：之后每次 `git commit` 会自动跑：

| 钩子 | 做什么 |
|------|--------|
| `ruff` | Lint，并尝试 `--fix` |
| `ruff-format` | 统一格式（行宽 100） |
| `mypy` | 对 `app` **严格**类型检查（`pyproject.toml` → `strict = true`） |

未执行 `pre-commit install` 时，提交不会触发检查，等于把门禁拆掉——**请不要跳过这一步。**

可选：对全库先扫一遍（首次或改配置后）：

```bash
pre-commit run --all-files
```

钩子失败 = 提交被拦；按终端提示改完再 `git commit`。不要用 `--no-verify` 绕过（除非紧急热修且事后补检）。PyCharm Terminal（已选中 `.venv`）执行即可，**不需要 uv**。

### 3. 启动

```bash
python main.py
```

或：

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

| 入口 | URL |
|------|-----|
| 根路径 | http://localhost:8000/ → 重定向登录 |
| 登录 | http://localhost:8000/login |
| 主应用 | http://localhost:8000/app |
| OpenAPI | http://localhost:8000/docs |

首次启动若无用户，自动创建默认管理员：**`admin` / `admin123`**（生产请立即修改）。

Windows 下跑临时脚本请开 UTF-8（见 `.cursor/rules/python-execution.mdc`）：

```powershell
python -X utf8 your_script.py
```

或设置环境变量 `PYTHONUTF8=1`。PowerShell 中不要用 `&&` 链接命令，用 `;` 或分行。

### 4. 应用配置（`.env`）

通过环境变量或项目根目录 `.env`（见 `app/config.py`、`.env.example`）：

| 配置项 | 说明 | 默认 |
|--------|------|------|
| `APP_ENV` | `development` / `production` / `test` | `development` |
| `HOST` / `PORT` | 监听地址 | `0.0.0.0` / `8000` |
| `DATABASE_URL` | 主库 | `sqlite:///./data/stamping_costing.db` |
| `AUXILIARY_DATABASE_URL` | 会话与异步任务 | `sqlite:///./data/auxiliary.db` |
| `PASSWORD_SALT` | 密码摘要盐 | 内置默认（生产务必覆盖） |
| `LOG_LEVEL` | 日志级别 | 随环境：开发 DEBUG / 生产 WARNING |
| `IS_DEBUG` | 调试模式 | 开发 `True` |
| `CORS_ORIGINS` | 跨域 | 开发 `*`；生产白名单 |
| `LLM_API_KEY` | AI 助理 API Key（OpenAI 兼容） | 空则 LLM 降级为规则摘要 |
| `LLM_MODEL` / `LLM_BASE_URL` | 模型与接口地址 | `deepseek-chat` / DeepSeek |
| `LLM_MAX_CONCURRENT_TASKS_PER_USER` | 每用户并发分析上限 | `2` |

---

## 开发工具：Ruff 与 Mypy（拴住动态语言）

配置集中在 **`pyproject.toml`**。目标不是「写起来爽」，而是 **契约可检查、风格不可争论、坏类型进不了主分支**。

| 工具 | 拴什么 |
|------|--------|
| **Ruff** | 格式与常见坑（未用导入、明显错误等） |
| **Mypy `strict`** | 函数签名、返回值、调用链上的类型；禁止「先写着、靠运行时猜」 |
| **pre-commit** | 把上面两道检查焊在 `git commit` 上 |

提交前本地也可手跑（与钩子等价）：

### Ruff（Lint + Format）

- 作用：替代/统一风格检查与格式化（行宽 **100**，目标 **py312**）
- 配置：`[tool.ruff]`

```bash
# 检查（可自动修复）
python -m ruff check app --fix

# 仅格式化
python -m ruff format app
```

### Mypy（严格类型检查）

- 作用：静态类型检查；本项目 **`strict = true`**
- 插件：`sqlalchemy.ext.mypy.plugin`、`pydantic.mypy`
- 配置：`[tool.mypy]`、`[tool.pydantic-mypy]`、若干 `[[tool.mypy.overrides]]`（Excel/openpyxl 等模块关闭部分噪音码）

```bash
# 在项目根目录执行（读取 pyproject.toml）
python -X utf8 -m mypy app
```

期望输出：`Success: no issues found in … source files`。

常用开关含义（已在配置中开启）：`disallow_untyped_defs`、`warn_return_any`、`disallow_untyped_calls` 等；第三方无 stubs 时 `ignore_missing_imports = true`。

### Pre-commit

配置文件：[`.pre-commit-config.yaml`](.pre-commit-config.yaml)。

> **提醒**：仅 `pip install pre-commit` 不够，必须再执行 **`pre-commit install`**，Git 才会挂上钩子（见上文 §2.1）。

日常也可手动全量跑：

```bash
pre-commit run --all-files
```

### 建议日常顺序

1. 在 PyCharm 中改代码  
2. Terminal：`python -m ruff check app --fix` → `python -m ruff format app`  
3. `python -X utf8 -m mypy app`  
4. Run uvicorn / `main.py`，浏览器打开 `/login`  

---

## 项目结构（摘要）

```
stamping-costing-platform/
├── main.py                 # FastAPI 入口、静态挂载、路由注册
├── app/
│   ├── common/             # 权限、审计、时区等横切
│   ├── routers/            # API：stamping / yishiyiyi / bom / costing / file_trace / llm / settings …
│   ├── services/           # 业务逻辑（含异步计算编排、LLM 分析）
│   ├── repositories/       # 数据访问
│   ├── models/             # ORM
│   ├── schemas/            # dto/ + vo/ + PageResult
│   ├── parsers/            # Excel 解析（stamping / 政策 / 基价 / bom …）
│   ├── deps/               # 鉴权 Depends
│   └── utils/              # ApiResponse、日志、迁移
├── static/
│   ├── index.html          # 主 SPA
│   ├── login.html          # 登录页
│   ├── css/style.css
│   └── js/
│       ├── main.js         # HttpClient / Toast / esc …
│       ├── app.js          # Hash 路由与页面注册
│       ├── permissions.js
│       ├── page-size.js
│       ├── llm-assistant/  # 顶栏 AI 助理浮窗
│       └── features/       # 与侧栏对齐的页面模块
├── docs/                   # 架构、前端、API 类型安全、权限等
├── data/                   # SQLite
├── uploads/                # 上传文件与简图
└── requirements.txt
```

前端页面与 Hash 对照见 `static/js/features/index.js` 的 `pageMeta` 与 `static/index.html` 侧栏。

---

## API 分组

完整路径与 Schema 以 **http://localhost:8000/docs** 为准。按前缀：

| 前缀 | 模块 |
|------|------|
| `/api/auth` | 登录、会话 me/touch/logout |
| `/api/dashboard` | 仪表盘统计 |
| `/api/stamping` | 零件/工序 |
| `/api/stamping/upload` | 工艺文件上传 |
| `/api/stamping/tonnage-price` | 冲次单价 |
| `/api/stamping/process-fees` | 冲压加工费 |
| `/api/yishiyiyi/policy` | 加减价政策 |
| `/api/yishiyiyi/base-price` | 基准价格 |
| `/api/yishiyiyi/winning-thickness` | 中标厚度一览 |
| `/api/yishiyiyi/scrap-price` | 废料月度销售价 |
| `/api/bom` | BOM 材料清单（上传 / 列表 / 产品结构） |
| `/api/bom/welding-unit-price` | 焊接单价 |
| `/api/bom/annual-part-price` | 年度零件价 |
| `/api/bom/packaging-transport-fee` | 包装运输费 |
| `/api/bom/welding-process-breakdown` | 焊接工艺拆解 |
| `/api/bom/welding-fees` | 焊接费 |
| `/api/costing/steel-price` | 钢材联动计算与列表 |
| `/api/costing/stamping-part-cost` | 零件价格计算与列表 |
| `/api/costing/assembly-costs` | 总成核价 |
| `/api/costing/monthly-bundle` | 月度核对合册导出 |
| `/api/costing/engine` | 自动核价引擎 |
| `/api/file-trace` | 文件溯源（列表 / 鉴权下载） |
| `/api/llm` | AI 助理：提交分析、轮询结果、分析历史 |
| `/api/settings/system` | 系统配置 |
| `/api/settings/users` | 用户与权限 |

业务接口需登录；除 `login` / `me` / `touch` / `logout` 外，一般使用 `require_perm(Perm.…)`。响应统一为：

```json
{ "code": 200, "success": true, "message": "…", "data": { } }
```

分页时 `data` 为 `PageResult`（`items` / `total` / `page` / `page_size` / …）。

### 前端调用示例

```javascript
// 登录后 HttpClient 自动带 Token
const res = await HttpClient.get('/api/stamping/parts/list', {
    params: { vehicle_model: 'T28', version: '1.0', skip: 0, limit: 20 }
});
// res.data.items / res.data.total

const formData = new FormData();
formData.append('file', fileInput.files[0]);
await HttpClient.post('/api/stamping/upload/', formData);
```

---

## 开发约定

| 文档 | 内容 |
|------|------|
| [文档目录](docs/README.md) | 按切片分目录的设计文档索引 |
| [架构说明](docs/architecture.md) | 分层 + 垂直切片导读 |
| [架构宪法](.cursor/rules/architecture-constitution.mdc) | 分层与切片依赖硬规则 |
| [前端规范](.cursor/rules/front-end.mdc) | SPA、Brabus、HUD 数据表 |
| [API 类型安全](.cursor/rules/api-type-safety.mdc) | `ApiResponse` / `PageResult` / 权限 Depends / `Any` 不进函数签名 |
| [权限设计](docs/permission-design.md) | 前后端权限码 |
| [生产安装（Windows 一键）](docs/deploy-windows-production.md) | 无 Python 环境用 `scripts/windows/setup.bat` |
| 云主机 Docker 手工发版 | 仓库根目录 `bash deploy.sh`（拉代码、构建、启动） |
| [命名规范](docs/naming-convention.mdc) | 标识符命名 |

要点：

- **Python 要拴死**：装依赖后必须 `pre-commit install`；勿用 `--no-verify` 常态绕过检查
- 前端：**禁止 Bootstrap**；样式以 Tailwind 任意值为主；列表表默认对齐 HUD 密表规范
- 后端：Router 不写 SQL、不调 Parser；Service 返回 VO；分页推荐 `ApiResponse.list_()`
- Python 脚本在 Windows 下建议：`python -X utf8 …`

---

## 许可证

MIT License
