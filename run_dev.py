import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# 前端根目录：扫描 static 下全部 .js（当前主要在 static/js）
STATIC_ROOT = ROOT / "static"


def run_step(args: list[str], description: str) -> None:
    print(f"🔍 [检查中] {description}...")
    # 使用 sys.executable -m 确保调用的永远是当前虚拟环境里的包
    result = subprocess.run([sys.executable, "-m", *args])
    if result.returncode != 0:
        print(f"\n❌ [{description}] 存在错误，已强行阻断 Uvicorn 服务启动！\n")
        sys.exit(result.returncode)


def resolve_node() -> str:
    """定位 node 可执行文件；未安装则阻断启动。"""
    node_path = shutil.which("node")
    if not node_path:
        print("\n❌ [Node 环境检查] 未找到 node，请先安装 Node.js 并加入 PATH。\n")
        sys.exit(1)
    return node_path


def run_node_check() -> None:
    """检查 Node 可用，并对 static/ 下全部前端 JS 做语法校验（node --check）。"""
    print("🔍 [检查中] Node JS 语法检查（static/）...")
    node_path = resolve_node()

    version = subprocess.run(
        [node_path, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    version_text = (version.stdout or version.stderr or "").strip() or "unknown"
    print(f"   Node: {version_text} ({node_path})")

    js_files = sorted(STATIC_ROOT.rglob("*.js"))
    if not js_files:
        print(f"⚠️  未找到 {STATIC_ROOT.relative_to(ROOT)} 下的 .js 文件，跳过语法检查")
        return

    failed: list[tuple[Path, str]] = []
    for js_path in js_files:
        result = subprocess.run(
            [node_path, "--check", str(js_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            failed.append((js_path, detail))

    if failed:
        print(f"\n❌ [Node JS 语法检查] {len(failed)}/{len(js_files)} 个文件失败：\n")
        for js_path, detail in failed:
            rel = js_path.relative_to(ROOT)
            print(f"  - {rel}")
            if detail:
                print(f"    {detail}")
        print("\n已强行阻断 Uvicorn 服务启动！\n")
        sys.exit(1)

    print(f"✅ Node JS 语法检查通过（static/ 共 {len(js_files)} 个文件）")


if __name__ == "__main__":
    # 1. 运行 Ruff 语法与导包规范检查
    run_step(["ruff", "check", "."], "Ruff 代码规范检查")

    # 2. 运行 Mypy 静态类型检查
    run_step(["mypy", "app/"], "Mypy 静态类型检查")

    # 3. Node 可用性 + 前端 JS 语法检查
    run_node_check()

    # 4. 拦截全部通过，拉起服务
    print("🚀 校验 100% 通过！正在启动 FastAPI 开发服务...\n")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--reload",
            "--reload-dir",
            "app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ]
    )
