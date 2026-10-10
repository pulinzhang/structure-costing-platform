"""启动前拦截未使用的函数和参数。

扫 ``main.py``、``run_dev.py``、``app/``、``scripts/``。测试目录不算引用：
只被测试调用的生产函数会在这里失败。

故意不报的误报：

- 路由 ``current_user``：``Depends(require_perm(...))`` 在依赖里鉴权，函数体可以不读。
- 路径参数：名字必须和 ``/{name}`` / ``/{name:int}`` 一致，FastAPI 按名绑定。
- ``dispatch``：Starlette ``BaseHTTPMiddleware`` 按方法名调用。
- ``Config``：Pydantic ``BaseSettings`` 按内部类名读取。
- ``@router.*`` / ``@app.*``、Pydantic 校验器与 ``computed_field``、SQLAlchemy ``listens_for``。
- 权限常量 ``Perm.*``（``vars(Perm)`` 读取）和 openpyxl 的 ``orientation`` 等属性赋值。
  扫描器看不到库代码和 ``vars()``，这两类不纳入本门禁。

::

    python -X utf8 -m scripts.check_unused_code
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATHS = (
    ROOT / "main.py",
    ROOT / "run_dev.py",
    ROOT / "app",
    ROOT / "scripts",
)

# 函数 / 方法 / property / 类。变量和属性赋值不扫（见模块说明）。
_REPORT_TYPES = frozenset({"function", "method", "property", "class"})
_IGNORE_NAMES = ("dispatch", "Config")
_IGNORE_DECORATORS = (
    "@router.*",
    "@app.*",
    "@field_validator",
    "@model_validator",
    "@field_serializer",
    "@computed_field",
    "@validator",
    "@*.listens_for",
)
_ARG_NAME_RE = re.compile(r"Unused function argument: `([A-Za-z_][A-Za-z0-9_]*)`")
_MIN_CONFIDENCE = 60


def _is_depends_call(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "Depends"
    return isinstance(func, ast.Attribute) and func.attr == "Depends"


def _arg_default(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> ast.AST | None:
    positional = fn.args.posonlyargs + fn.args.args
    offset = len(positional) - len(fn.args.defaults)
    for index, arg in enumerate(positional):
        if arg.arg != name:
            continue
        default_index = index - offset
        if default_index < 0:
            return None
        return fn.args.defaults[default_index]
    for arg, default in zip(fn.args.kwonlyargs, fn.args.kw_defaults, strict=True):
        if arg.arg == name:
            return default
    return None


def _path_param_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    pattern = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(?::[^}]+)?\}")
    for decorator in fn.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        for arg in decorator.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                names.update(pattern.findall(arg.value))
    return names


def _function_at_line(tree: ast.AST, line: int) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    found: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        end_line = getattr(node, "end_lineno", None) or node.lineno
        if node.lineno <= line <= end_line and (found is None or node.lineno >= found.lineno):
            found = node
    return found


def _allows_unused_argument(
    tree: ast.AST,
    line: int,
    arg_name: str,
) -> bool:
    fn = _function_at_line(tree, line)
    if fn is None:
        return False
    if arg_name in _path_param_names(fn):
        return True
    return arg_name == "current_user" and _is_depends_call(_arg_default(fn, arg_name))


def _load_trees(paths: set[Path]) -> dict[Path, ast.AST]:
    trees: dict[Path, ast.AST] = {}
    for path in paths:
        trees[path] = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return trees


def unused_argument_findings() -> list[str]:
    """Ruff ARG 里去掉框架签名后仍未使用的参数。"""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "app",
            "scripts",
            "main.py",
            "run_dev.py",
            "--select",
            "ARG",
            "--output-format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode not in (0, 1):
        detail = (proc.stderr or proc.stdout or "").strip()
        return [f"Ruff ARG 检查失败：{detail or proc.returncode}"]
    payload = json.loads(proc.stdout or "[]")
    if not isinstance(payload, list):
        return ["Ruff ARG 输出不是列表"]

    paths: set[Path] = set()
    pending: list[tuple[Path, int, str]] = []
    for item in payload:
        if not isinstance(item, dict) or item.get("code") not in {"ARG001", "ARG002", "ARG003"}:
            continue
        message = str(item.get("message", ""))
        matched = _ARG_NAME_RE.search(message)
        if matched is None:
            continue
        filename = Path(str(item.get("filename", "")))
        if not filename.is_absolute():
            filename = ROOT / filename
        location = item.get("location")
        if not isinstance(location, dict):
            continue
        pending.append((filename, int(location.get("row", 1)), matched.group(1)))
        paths.add(filename)

    trees = _load_trees(paths)
    findings: list[str] = []
    for filename, line, arg_name in pending:
        if _allows_unused_argument(trees[filename], line, arg_name):
            continue
        rel = filename.relative_to(ROOT)
        findings.append(f"{rel}:{line}: 未使用参数 {arg_name}")
    return findings


def unused_code_findings() -> list[str]:
    """Vulture 未使用的函数、方法、property、类；排除框架回调。"""
    try:
        from vulture import Vulture
    except ImportError:
        return ["未安装 vulture。请执行：python -m pip install vulture"]

    vulture = Vulture(ignore_names=list(_IGNORE_NAMES), ignore_decorators=list(_IGNORE_DECORATORS))
    vulture.scavenge([str(path) for path in SCAN_PATHS], exclude=["*__pycache__*"])
    findings: list[str] = []
    for item in vulture.get_unused_code(min_confidence=_MIN_CONFIDENCE):
        if item.typ not in _REPORT_TYPES:
            continue
        filename = Path(item.filename)
        try:
            rel = filename.relative_to(ROOT)
        except ValueError:
            rel = filename
        findings.append(f"{rel}:{item.first_lineno}: 未使用{item.typ} {item.name}")
    return findings


def main() -> int:
    findings = unused_argument_findings() + unused_code_findings()
    if findings:
        print(f"未使用代码 {len(findings)} 处：\n")
        for line in findings:
            print(f"  {line}")
        return 1
    print("✅ 无未使用代码")
    return 0


if __name__ == "__main__":
    sys.exit(main())
