"""校验 Pydantic ``model_config`` 必须用 ``ConfigDict``（零例外）。

禁止 ``model_config = {"from_attributes": True}`` 等可变 dict 字面量。
Ruff ``RUF012`` **不**拦 pydantic 的 ``model_config`` 赋值，故本守卫是硬门禁。
细则：``.cursor/rules/api-type-safety.mdc`` §7。不通过不准合并。

::

    python -X utf8 -m scripts.check_model_config
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (
    ROOT / "app" / "schemas",
    ROOT / "app" / "repositories",
)


def _is_config_dict_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "ConfigDict":
        return True
    return isinstance(func, ast.Attribute) and func.attr == "ConfigDict"


def find_model_config_violations() -> list[str]:
    """返回违规报告行：``model_config`` 不是 ``ConfigDict(...)``。"""
    violations: list[str] = []
    for scan_root in SCAN_ROOTS:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(text, filename=str(path))
            except SyntaxError as err:
                rel = path.relative_to(ROOT).as_posix()
                violations.append(f"{rel}:1  syntax error: {err}")
                continue
            rel = path.relative_to(ROOT).as_posix()
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for stmt in node.body:
                    target_names: list[str] = []
                    value: ast.AST | None = None
                    if isinstance(stmt, ast.Assign):
                        value = stmt.value
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                target_names.append(target.id)
                    elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        target_names.append(stmt.target.id)
                        value = stmt.value
                    if "model_config" not in target_names or value is None:
                        continue
                    if _is_config_dict_call(value):
                        continue
                    kind = type(value).__name__
                    violations.append(
                        f"{rel}:{stmt.lineno}  class={node.name}  "
                        f"model_config must be ConfigDict(...), got {kind}"
                    )
    return violations


def main() -> int:
    violations = find_model_config_violations()
    if violations:
        print(
            "model_config must be ConfigDict(from_attributes=True) (or ConfigDict(...))",
            file=sys.stderr,
        )
        for line in violations:
            print(line, file=sys.stderr)
        print(f"\n{len(violations)} violation(s). See api-type-safety.mdc §7.", file=sys.stderr)
        return 1
    print("ok: model_config uses ConfigDict only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
