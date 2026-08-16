"""
生产启动入口：先 Schema 升级（失败则不启动）→ 可选字节码预编译 → 多 Worker Uvicorn。

用法（仓库根目录、已激活 venv）：
  set APP_ENV=production
  python run_prod.py

Windows 脚本 ``scripts/windows/start.bat`` / 服务安装亦指向本文件。

说明：
- 本仓库无 Alembic；升级走 ``app.bootstrap.schema_upgrade``（与 main lifespan 同源）。
- 多 Worker 前先单进程升级，避免 N 个 worker 同时 ALTER SQLite。
"""

from __future__ import annotations

import os
import subprocess
import sys


def run_step(cmd: list[str], description: str) -> None:
    print(f"[生产前置] {description} ...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n[失败] {description}，阻断生产服务启动（exit={result.returncode}）\n")
        sys.exit(result.returncode)


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
                if key == "UVICORN_WORKERS" and "UVICORN_WORKERS" not in os.environ:
                    if value.isdigit() and int(value) > 0:
                        workers = int(value)
                if key == "PORT" and "PORT" not in os.environ:
                    if value.isdigit() and int(value) > 0:
                        port = int(value)
    except OSError:
        pass
    return workers, port


if __name__ == "__main__":
    os.environ.setdefault("APP_ENV", "production")
    os.environ.setdefault("PYTHONUTF8", "1")

    # 1. Schema 升级（失败则不启动）
    run_step(
        [sys.executable, "-m", "app.bootstrap.schema_upgrade"],
        "数据库 Schema 自动升级",
    )

    # 2. 预编译字节码（可选加速冷启动；失败不阻断）
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

    # 3. 多进程服务（无 --reload）
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
