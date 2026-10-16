[English](README.md) · **简体中文**

# 结构件自动核价平台

汽车结构件的月度核价：总成、分总成、冲压件。工艺确认表、一事一议钢价、材料清单和工程变更进同一套系统。价格在领域层算完。助理只解释核价库里已经得出的数。

深色作业台。碳素黑、钛灰面板、标志性红。

---

## 产品

<p>
  <img src="static/helper/img/01-dashboard.png" width="49%" alt="管理者看板：本期产出、待办缺口与核价就绪" />
  <img src="static/helper/img/18-costing-engine.png" width="49%" alt="月度核价引擎：就绪检查、运行历史与审计" />
</p>
<p>
  <img src="static/helper/img/16-stamping-part-cost.png" width="49%" alt="冲压零件价格：材料、加工与单件成本" />
  <img src="static/helper/img/28-llm-assistant.png" width="49%" alt="AI 助理用自然语言解读已核算期间" />
</p>

采购月结按固定顺序走。源表入库，钢价随钢厂联动，冲压件拆成材料加加工，焊接与外购折入，总成价是财务和采购共同阅读的那一列。就绪门禁会拦住引擎：该基地、该月的废料价、政策和费用不齐，就不能开算。每一次运行有编号、耗时和留痕。

问「芜湖 T13J 二月核算得怎么样」，回答引用的是表格里的同一批行：外购、冲压、焊接、间接费。模型不负责编一个价格。

---

## 范围

| 领域 | 里面有什么 |
|------|------------|
| **主数据** | 基地、项目、供应商、牌号、钢厂 |
| **冲压工程** | 工艺确认表、零件与工序、冲次单价、模具费与检具费、加工费 |
| **一事一议** | 厚度 / 宽度 / 锌层加减价、基准价格、中标厚度、废料月度销售价 |
| **焊接与 BOM** | 缩进式材料清单与简图、焊接单价、年度零件价、包装运输费、焊接工艺拆解、焊接费 |
| **工程变更** | 设变与材变，下一期核价必须看见 |
| **核价** | 钢材联动、零件价格、总成核价、月度引擎、核对导出、采购价格协议 |
| **文件溯源** | 已归档工作簿，按同一套权限码筛选和下载 |
| **AI 助理** | 对已核算期间用自然语言提问；Markdown 回答、历史、打印与 Word 导出 |
| **访问控制** | 登录；路由与侧栏使用同一套角色权限码；操作日志 |

典型路径：工艺、政策、基价、废料价、BOM 入库 → 钢材联动 → 零件核价 → 总成核价 → 引擎 → 解读。

---

## 工程取舍

仓库是垂直切片的单体。每个业务域（`stamping`、`yishiyiyi`、`bom`、`costing`、`llm` 等）自己带路由、服务、仓储、模型和 Excel 解析器。调用只往一个方向走：

```
Router → Service → Repository → Database
```

解析器是纯函数，只允许 Service 调用。上游切片不引用核价。核价去组合主数据、冲压、一事一议和 BOM。LLM 切片只读结果表，定价引擎不依赖它。

几条让这套长期核价代码还能被评审的规则：

- **数字留在领域层。** Service 返回类型化的视图对象。JSON 经 `ApiResponse[T]` 和 `PageResult` 出去。Decimal 与时间的形态写在 Schema 上，不写在路由里。
- **月度引擎只指挥。** 准备范围、跑流水线、落库。编排器不按零件循环，也不写 SQL。
- **长任务靠轮询。** 上传和计算返回 `task_id`。请求上的数据库会话不会带进工作线程。
- **权限是权限码。** 路由上要求 `Perm.*`，SPA 侧栏用同一套码。藏起菜单不等于关掉接口。
- **提交前先检查 Python。** Ruff 按 100 列格式化。Mypy 对 `app/` 开 `strict`，挂在 pre-commit 上。
- **工作簿仍是证据。** 导入文件归档并登记。价格行可以指回钢厂文件和当初的单元格范围。

架构导读：[docs/architecture.md](docs/architecture.md)。

---

## 技术栈

| | |
|--|--|
| 接口 | FastAPI、Pydantic v2、SQLAlchemy 2 |
| 数据 | SQLite（主库 `data/stamping_costing.db`，会话与任务在 `data/auxiliary.db`） |
| 工作簿 | OpenPyXL、xlrd；简图用 Pillow |
| 界面 | `static/` 里的 ES Module SPA。Hash 路由、随仓库提交的 Tailwind，没有打包器 |
| 鉴权 | Token（`X-Token` 或 Bearer）加权限码 |
| 助理 | OpenAI 兼容的对话接口。`LLM_API_KEY` 为空时退回规则摘要 |
| 交付 | Windows 一键安装，或用 `deploy.sh` 打 Docker |

Python **3.12+**。许可证 **MIT**。

---

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
copy .env.example .env
pre-commit install
python main.py
```

macOS / Linux：`source .venv/bin/activate`，然后 `cp .env.example .env`。

| | |
|--|--|
| 应用 | http://localhost:8000/app |
| 登录 | http://localhost:8000/login |
| OpenAPI | http://localhost:8000/docs |

用户表为空时，首次启动会创建 **`admin` / `admin123`**。放到共享环境之前先改掉。

配置在 `.env`（见 `.env.example` 与 `app/config.py`）。会改变行为的几项：

| 变量 | 作用 | 默认 |
|------|------|------|
| `APP_ENV` | `development` / `production` / `test` | `development` |
| `DATABASE_URL` | 主库 | `sqlite:///./data/stamping_costing.db` |
| `PASSWORD_SALT` | 密码摘要盐 | 内置默认；生产环境请覆盖 |
| `LLM_API_KEY` | 助理密钥 | 空则规则摘要 |
| `LLM_MODEL` / `LLM_BASE_URL` | 模型与地址 | `deepseek-chat` / DeepSeek |

Windows 上临时脚本请开 UTF-8：`python -X utf8 script.py`。PowerShell 里用 `;` 串联命令。

与提交钩子相同的检查：

```powershell
python -m ruff check app --fix
python -m ruff format app
python -X utf8 -m mypy app
```

部署说明：[Windows 生产安装](docs/deploy-windows-production.md)（目标机可以没有 Python，走 `scripts\windows\setup.bat`）；云主机在仓库根目录执行 `bash deploy.sh`。

---

## 目录

```
stamping-costing-platform/
├── main.py                  # 应用装配、静态挂载、路由注册
├── app/
│   ├── routers/             # 只处理 HTTP：取参、返回
│   ├── services/            # 规则、事务、解析器、长任务
│   ├── repositories/        # 查询
│   ├── models/              # 表
│   ├── schemas/             # dto/ 与 vo/
│   └── parsers/             # Excel 进、行出
├── static/                  # SPA、登录页、AI 助理浮窗
├── docs/                    # 架构与各切片设计
├── data/                    # SQLite
└── uploads/                 # 归档工作簿与简图
```

页面对齐侧栏：`static/js/features/`。

---

## 接着读

| | |
|--|--|
| [架构说明](docs/architecture.md) | 分层、切片，以及依赖箭头为什么这样指 |
| [文档目录](docs/README.md) | 各切片设计笔记 |
| [权限设计](docs/permission-design.md) | 权限码如何授予、如何拦截 |
| [AI 核价解读](docs/llm/llm-costing-analysis-report-design.md) | 助理被允许说什么 |
| [Windows 部署](docs/deploy-windows-production.md) | 目标机无需 Python 工具链 |

---

## 许可证

MIT
