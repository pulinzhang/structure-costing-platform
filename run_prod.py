"""
生产启动入口：可选字节码预编译 → 多 Worker Uvicorn。

用法（仓库根目录、已激活 venv）：
  set APP_ENV=production
  python run_prod.py

Windows 脚本 ``scripts/windows/start.bat`` / 服务安装亦指向本文件。

说明：
- 本项目为教学/开发交付；空库由 ``main`` lifespan 中 ``create_all`` 建表，不做 Schema 升库。
- 结构变更时请删库或换新库文件后重启（见部署文档）。
"""

from __future__ import annotations

import os
import subprocess
import sys


def _resolve_workers() -> int:
    raw = os.getenv("UVICORN_WORKERS", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    cpu_cores = os.cpu_count() or 2
    # 默认偏保守，兼顾 SQLite；可用环境变量显式拉高
    return max(2, min(cpu_cores * 2 + 1, 8))


def _load_dotenv_workers_port() -> tuple[int, int]:
    """粗读 .env 中的 UVICORN_WORKERS / PORT（不覆盖已有环境变量）。"""
    workers = _resolve_workers()
    port = int(os.getenv("PORT", "8000") or "8000")
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return workers, port
    try:
        with open(env_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if (
                    key == "UVICORN_WORKERS"
                    and "UVICORN_WORKERS" not in os.environ
                    and value.isdigit()
                    and int(value) > 0
                ):
                    workers = int(value)
                if (
                    key == "PORT"
                    and "PORT" not in os.environ
                    and value.isdigit()
                    and int(value) > 0
                ):
                    port = int(value)
    except OSError:
        pass
    return workers, port


if __name__ == "__main__":
    os.environ.setdefault("APP_ENV", "production")
    os.environ.setdefault("PYTHONUTF8", "1")

    # 1. 预编译字节码（可选加速冷启动；失败不阻断）
    compile_result = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "app"],
    )
    if compile_result.returncode != 0:
        print("[警告] 字节码预编译失败，继续启动服务")
    else:
        print("[生产前置] Python 字节码预编译 ... 完成")

    workers, port = _load_dotenv_workers_port()
    host = os.getenv("HOST", "0.0.0.0")

    print(
        f"正在启动生产 Uvicorn "
        f"(host={host}, port={port}, workers={workers}, APP_ENV={os.environ.get('APP_ENV')})...\n"
    )

    # 2. 多进程服务（无 --reload）
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--workers",
            str(workers),
            "--log-level",
            "warning",
            "--no-access-log",
        ]
    )
    sys.exit(result.returncode)
