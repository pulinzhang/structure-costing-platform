# Windows 生产环境安装说明

> 适用于内网 / 单机 Windows 服务器部署。  
> 开发环境见根目录 [README.md](../README.md)；云部署另见 [deploy-zeabur.md](./deploy-zeabur.md)。

---

## 1. 适用场景

| 场景 | 做法 |
|------|------|
| 全新电脑，**没有安装过 Python** | 双击 / 管理员运行 `scripts\windows\setup.bat` 一键安装 |
| 已有 Python 3.12+ | 仍可用 `setup.bat`（会跳过装 Python，只建 venv 与依赖） |
| 日常启停 | `scripts\windows\start.bat` / `stop.bat` |

目标：装好后浏览器访问：

- 登录：`http://服务器IP:8000/login`
- 主应用：`http://服务器IP:8000/app`
- API 文档：生产环境建议关闭对外暴露 `/docs`（当前版本仍可用，请靠防火墙限制）

---

## 2. 机器要求

| 项 | 要求 |
|----|------|
| 系统 | Windows 10 / 11 / Server 2016+（64 位） |
| 权限 | 建议**管理员**运行 `setup.bat`（便于写 PATH、放行防火墙） |
| 网络 | 首次安装需能访问外网：下载 Python、pip 依赖（内网见 §6） |
| 磁盘 | 建议 ≥ 2GB 空闲（含 Python + venv + 上传目录） |
| 端口 | 默认 **8000**（可在 `.env` 修改） |

---

## 3. 一键安装（无 Python 环境）

1. 将本仓库完整拷贝到目标机，例如：`D:\stamping-costing-platform`
2. 右键 **`scripts\windows\setup.bat`** → **以管理员身份运行**
3. 按提示等待结束（会自动：安装 Python 3.12 → 建 `.venv` → `pip install -r requirements.txt` → 生成生产 `.env` → 可选放行防火墙）
4. 用记事本打开项目根目录 **`.env`**，至少修改：
   - `PASSWORD_SALT`（随机长字符串）
   - `CORS_ORIGINS`（写成前端实际访问来源，见 §5）
5. 双击 **`scripts\windows\start.bat`** 启动
6. 浏览器打开 `http://本机IP:8000/login`  
   - 默认管理员：`admin` / `admin123` → **登录后立刻改密**

安装脚本位置：

```
scripts/windows/
  setup.bat      ← 入口（双击）
  setup.ps1      ← 实际安装逻辑
  start.bat      ← 生产启动
  stop.bat       ← 停止（结束占用端口的进程）
```

命令行等价：

```bat
cd /d D:\stamping-costing-platform
scripts\windows\setup.bat
scripts\windows\start.bat
```

---

## 4. 安装脚本做了什么

`setup.ps1` 按顺序：

1. 定位仓库根目录（`scripts\windows` 的上两级）
2. 检测是否已有可用的 `python` / `py -3.12`（版本 ≥ 3.12）
3. 若没有：
   - 优先 `winget install Python.Python.3.12`
   - 失败则从 python.org 下载官方安装包并**静默安装**（`PrependPath=1`）
4. `python -m venv .venv`
5. `.venv\Scripts\python.exe -m pip install -U pip`
6. `.venv\Scripts\pip.exe install -r requirements.txt`（**不含**开发用 ruff/mypy）
7. 若不存在 `.env`：从 `.env.production.example` 复制
8. 创建 `data\`、`uploads\`、`logs\`
9. （管理员时）尝试 `netsh advfirewall` 放行 TCP 8000

> 生产环境**不要**装 `requirements-dev.txt`，也**不要**装 pre-commit 钩子。

---

## 5. 生产 `.env` 必改项

模板文件：[`.env.production.example`](../.env.production.example)。`setup.bat` 会在缺少 `.env` 时复制一份。

| 变量 | 生产建议 |
|------|----------|
| `APP_ENV` | 必须 `production`（关闭 DEBUG / reload，日志 WARNING） |
| `HOST` | `0.0.0.0`（局域网可访问） |
| `PORT` | `8000` 或按需 |
| `UVICORN_WORKERS` | 默认 `4`；SQLite 写锁多时可改为 `2` |
| `PASSWORD_SALT` | **必改**，与开发机不同的随机串 |
| `DEBUG` | `False` |
| `LOG_LEVEL` | `WARNING` |
| `CORS_ORIGINS` | JSON 数组，包含实际前端来源，例如 `["http://10.0.0.8:8000"]`（同源部署通常也写上访问用的 origin） |
| `DATABASE_URL` | 默认可用；务必定期备份 `data\*.db` |
| `AUXILIARY_DATABASE_URL` | 会话/异步任务库，一并备份 |

同源由本服务同时提供 `/login` 与 `/api` 时，仍建议把浏览器地址栏里的 origin 写进 `CORS_ORIGINS`。

---

## 6. 无外网 / 离线安装

1. 在有网机器上准备：
   - Python 3.12 Windows 安装包（amd64），放到 `scripts\windows\vendor\python-3.12.x-amd64.exe`
   - 或事先打好 wheel 包目录（`pip download -r requirements.txt -d scripts\windows\vendor\wheels`）
2. 拷贝整个仓库到离线机
3. 运行 `setup.bat`：若检测到 `vendor\` 下的安装包，会优先本地静默安装 Python
4. 离线 pip：

```bat
.venv\Scripts\pip.exe install --no-index --find-links=scripts\windows\vendor\wheels -r requirements.txt
```

（`setup.ps1` 若检测到 `vendor\wheels` 会自动走离线安装。）

---

## 7. 启停与开机自启

### 7.1 手动启停

```bat
scripts\windows\start.bat
scripts\windows\stop.bat
```

`start.bat` 会设置 `APP_ENV=production`、`PYTHONUTF8=1`，默认 **`--workers 4`**（无 `--reload`）。  
进程数读 `.env` 的 `UVICORN_WORKERS`（没有则 4）。关掉黑窗口即停服。

### 7.2 多 Worker 说明（内网 / 涉密机）

本项目按**内网部署、不连外网**设计即可；多 worker 与是否联网无关。

```text
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

| 项 | 说明 |
|----|------|
| 默认 | `UVICORN_WORKERS=4`（见 `.env.production.example`） |
| 修改 | 改 `.env` 后：窗口版重开 `start.bat`；服务版需**重新**管理员运行 `install-service.bat` |
| 建议范围 | 一般 **2～4**；机器核数少可设 2 |
| SQLite | 多进程会争用同一库文件。读多写少通常可接受；核价/上传高峰若出现 `database is locked`，先降到 `2`，并保证 `data\` 在本地磁盘（勿放网盘） |
| Windows | 使用 uvicorn 自带 `--workers`（勿用 Linux 专用的 gunicorn） |
| 涉密离线 | 服务安装用的 NSSM 请预先放到 `scripts\windows\vendor\nssm\win64\nssm.exe`，不要依赖外网下载 |

### 7.3 注册为 Windows 服务（推荐）

可以。装好 `setup.bat` 并配好 `.env` 后，用 **NSSM** 把 uvicorn 包成系统服务：开机自启、崩溃自动拉起、不依赖登录桌面。

**一键安装（管理员）：**

```bat
scripts\windows\install-service.bat
```

脚本会：

1. 确认已有 `.venv` 与 `.env`
2. 优先使用本地 `scripts\windows\vendor\nssm\`（**涉密机请离线放好**）；没有才尝试下载
3. 注册服务名：**`StampingCostingPlatform`**
4. 工作目录 = 仓库根；启动参数含 `.env` 中的 `UVICORN_WORKERS` / `PORT`，例如：  
   `.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4`
5. 环境变量：`APP_ENV=production`、`PYTHONUTF8=1`
6. 标准输出/错误写入 `logs\service-stdout.log`、`logs\service-stderr.log`
7. 启动类型：自动；异常退出约 5 秒后重启
8. 立即 `start` 服务

### 7.4 卸载与日常管理

```bat
scripts\windows\uninstall-service.bat
```

**日常管理：**

```bat
net start StampingCostingPlatform
net stop StampingCostingPlatform
sc query StampingCostingPlatform
```

或：`Win + R` → `services.msc` → 找到「汽车冲压件自动核价平台」。

**离线 NSSM：**  
无外网时，从 https://nssm.cc/download 下载，解压后把 `win64\nssm.exe` 放到：

```
scripts\windows\vendor\nssm\win64\nssm.exe
```

再跑 `install-service.bat`。

**注意：**

| 点 | 说明 |
|----|------|
| 必须管理员 | 注册/删除服务需要提权 |
| 先改 `.env` | 服务进程读的是项目根 `.env`；改完后 `net stop` 再 `net start` |
| 改代码/依赖后 | 重启服务即可；大版本升级建议先 `stop` 再更新文件 |
| 与 `start.bat` | 不要同时用窗口版和系统服务占同一端口 |
| 备份 | `data\`、`uploads\` 仍需自行备份；服务本身不负责备份 |

### 7.5 备选：任务计划程序（非真正服务）

不想装 NSSM 时：

1. 打开「任务计划程序」
2. 创建基本任务 → 触发器选「计算机启动时」或「用户登录时」
3. 操作：启动程序  
   - 程序：`D:\...\仓库\.venv\Scripts\python.exe`  
   - 参数：`-m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level warning`  
   - 起始于：仓库根目录  
4. 在「常规」勾选「不管用户是否登录都要运行」（需管理员），并配置环境变量较麻烦  

更推荐 §7.3 的正式服务方式。

---

## 8. 上线检查清单

- [ ] 已执行 `setup.bat`，`.venv` 存在  
- [ ] `.env` 中 `APP_ENV=production`，`PASSWORD_SALT` 已改  
- [ ] `CORS_ORIGINS` 含真实访问地址  
- [ ] 防火墙已放行端口（或仅内网可达）  
- [ ] 默认 `admin` / `admin123` 已改密  
- [ ] `data\`、`uploads\` 纳入备份策略  
- [ ] `start.bat` 或 **Windows 服务** 能访问 `/login` 与 `/app`  
- [ ] （若用服务）已管理员执行 `install-service.bat`，`services.msc` 中状态为“正在运行”

---

## 9. 常见问题

| 现象 | 处理 |
|------|------|
| `python` 不是内部或外部命令 | 重新开一个 cmd 再跑 `setup.bat`；或注销/重启以刷新 PATH |
| winget 不可用 | 脚本会改走官网安装包；也可把安装包放到 `scripts\windows\vendor\` |
| pip 很慢/超时 | 可设镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 局域网打不开 | 检查 `HOST=0.0.0.0`、防火墙、本机 IP；用 `http://IP:8000/login` |
| 服务起不来 | 看 `logs\service-stderr.log`；确认 `.env`、端口未被占用；`sc query StampingCostingPlatform` |
| 改 `.env` 不生效 | `net stop StampingCostingPlatform` 后再 `net start` |
| 提交代码相关的 Ruff/Mypy | 那是**开发机**要求；生产机只装运行依赖即可 |

---

## 10. 与开发环境的区别

| | 开发（README） | 生产（本文） |
|--|----------------|--------------|
| Python 工具链 | Ruff / Mypy / pre-commit | 不装 |
| 启动 | `--reload`、DEBUG | 无 reload、`APP_ENV=production` |
| 依赖 | `requirements.txt` + `requirements-dev.txt` | 仅 `requirements.txt` |
| 密码盐 / CORS | 可用默认 | **必须改** |
