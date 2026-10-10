"""启动前拦截签名和类型声明里新增的显式 ``Any``。

``Any`` 不过函数边界（api-type-safety §2）：参数、返回值、类字段、模块级注解和类型别名都不许新写 ``Any``。
函数体内可以暂时接住第三方或 ``json.loads`` 的结果，离开前必须收窄；``cast(...)`` 留在体内，不在本检查范围。

存量记在 ``scripts/explicit_any_baseline.txt``。某一处的出现次数超过基线即失败；删掉存量不用改基线也能通过。

::

    python -X utf8 -m scripts.check_explicit_any
"""

from __future__ import annotations

import ast
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = Path(__file__).resolve().parent / "explicit_any_baseline.txt"
SCAN_PATHS = (
    ROOT / "main.py",
    ROOT / "run_dev.py",
    ROOT / "app",
    ROOT / "scripts",
)


def _annotation_uses_any(node: ast.AST | None) -> bool:
    if node is None:
        return False
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id == "Any":
            return True
        if isinstance(child, ast.Attribute) and child.attr == "Any":
            return True
    return False


def _signature_hits(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[int]:
    lines: list[int] = []
    arguments = fn.args
    slots = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
    for arg in slots:
        if _annotation_uses_any(arg.annotation):
            lines.append(arg.lineno)
    for arg in (arguments.vararg, arguments.kwarg):
        if arg is not None and _annotation_uses_any(arg.annotation):
            lines.append(arg.lineno)
    if _annotation_uses_any(fn.returns):
        assert fn.returns is not None
        lines.append(fn.returns.lineno)
    return lines


def _assigned_name(stmt: ast.stmt) -> str:
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return stmt.target.id
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
        target = stmt.targets[0]
        if isinstance(target, ast.Name):
            return target.id
    if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return stmt.name
    return "<expr>"


def _walk(body: list[ast.stmt], qual: str, rel: str, hits: list[tuple[str, int, str]]) -> None:
    """类体和模块体上的注解、别名、函数签名。函数体内部的临时标注不扫。"""
    for stmt in body:
        prefix = f"{qual}." if qual else ""
        if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
            name = f"{prefix}{stmt.name}"
            hits.extend((rel, line, name) for line in _signature_hits(stmt))
            continue
        if isinstance(stmt, ast.ClassDef):
            _walk(stmt.body, f"{prefix}{stmt.name}", rel, hits)
            continue
        if isinstance(stmt, ast.AnnAssign) and _annotation_uses_any(stmt.annotation):
            hits.append((rel, stmt.lineno, f"{prefix}{_assigned_name(stmt)}"))
            continue
        if isinstance(stmt, ast.Assign) and _annotation_uses_any(stmt.value):
            hits.append((rel, stmt.lineno, f"{prefix}{_assigned_name(stmt)}"))


def explicit_any_hits() -> list[tuple[str, int, str]]:
    """返回 ``(相对路径, 行号, 限定名)``。同一签名上每处 ``Any`` 记一条。"""
    hits: list[tuple[str, int, str]] = []
    files: list[Path] = []
    for path in SCAN_PATHS:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(
                sorted(item for item in path.rglob("*.py") if "__pycache__" not in item.parts)
            )
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as err:
            hits.append((rel, 1, f"语法错误 {err}"))
            continue
        _walk(tree.body, "", rel, hits)
    return hits


def _counts(hits: list[tuple[str, int, str]]) -> Counter[str]:
    counted: Counter[str] = Counter()
    for rel, _line, name in hits:
        counted[f"{rel}:{name}"] += 1
    return counted


def load_baseline() -> Counter[str]:
    if not BASELINE_PATH.is_file():
        return Counter()
    counted: Counter[str] = Counter()
    for raw in BASELINE_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, count_text = line.rpartition(" ")
        counted[key] = int(count_text)
    return counted


def new_explicit_any(hits: list[tuple[str, int, str]] | None = None) -> list[str]:
    """超过基线的签名 ``Any``。基线里已删掉的条目不报。"""
    found = explicit_any_hits() if hits is None else hits
    allowed = load_baseline()
    current = _counts(found)
    lines_of: dict[str, list[int]] = {}
    for rel, line, name in found:
        lines_of.setdefault(f"{rel}:{name}", []).append(line)

    findings: list[str] = []
    for key in sorted(current):
        extra = current[key] - allowed.get(key, 0)
        if extra <= 0:
            continue
        lines = ", ".join(str(line) for line in sorted(set(lines_of[key])))
        findings.append(f"{key} 有 {current[key]} 处 Any（基线 {allowed.get(key, 0)}），行 {lines}")
    return findings


def main() -> int:
    hits = explicit_any_hits()
    findings = new_explicit_any(hits)
    if findings:
        print(f"签名或类型声明中新增 Any {len(findings)} 处：\n")
        for line in findings:
            print(f"  {line}")
        print("\n存量见 scripts/explicit_any_baseline.txt。新代码请改用具体类型或 object。")
        return 1
    current = sum(_counts(hits).values())
    print(f"✅ 没有新增的签名 Any（存量 {current} 处）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
