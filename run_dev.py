import subprocess
import sys

def run_step(args: list[str], description: str) -> None:
    print(f"🔍 [检查中] {description}...")
    # 使用 sys.executable -m 确保调用的永远是当前虚拟环境里的包
    result = subprocess.run([sys.executable, "-m"] + args)
    if result.returncode != 0:
        print(f"\n❌ [{description}] 存在错误，已强行阻断 Uvicorn 服务启动！\n")
        sys.exit(result.returncode)

if __name__ == "__main__":
    # 1. 运行 Ruff 语法与导包规范检查
    run_step(["ruff", "check", "."], "Ruff 代码规范检查")

    # 2. 运行 Mypy 静态类型检查
    run_step(["mypy", "app/"], "Mypy 静态类型检查")

    # 3. 拦截全部通过，拉起服务
    print("🚀 校验 100% 通过！正在启动 FastAPI 开发服务...\n")
    subprocess.run([
        sys.executable, "-m", "uvicorn", "main:app",
        "--reload", "--host", "0.0.0.0", "--port", "8000"
    ])