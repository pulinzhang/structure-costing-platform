"""校验 Router 整数路径参数（零例外，必须 exit 0）。

强制：注解为 int 的路径参数必须 ``/{name:int}``，禁止裸 ``/{name}``。
细则：.cursor/rules/api-type-safety.mdc §6。不通过不准合并。

::

    python -X utf8 -m scripts.check_route_path_params
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "routers"

DECORATOR_RE = re.compile(
    r"""(@router\.(?:get|put|post|patch|delete)\(\s*(?:\r?\n\s*)*)(["'])([^"']+)(["'])""",
    re.MULTILINE,
)
PARAM_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-zA-Z_][a-zA-Z0-9_]*))?\}")


def _func_annotations(text: str, decorator_end: int) -> dict[str, str]:
    rest = text[decorator_end:]
    def_match = re.search(r"\ndef\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(", rest)
    if not def_match:
        return {}
    abs_start = decorator_end + def_match.start()
    paren = text.find("(", abs_start)
    depth = 0
    end: int | None = None
    for index in range(paren, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                end = index
                break
    if end is None:
        return {}
    result: dict[str, str] = {}
    for part in text[paren + 1 : end].split(","):
        part = part.strip()
        if not part or part.startswith("*"):
            continue
        name_type = part.split("=", 1)[0].strip()
        if ":" not in name_type:
            continue
        name, annotation = name_type.split(":", 1)
        result[name.strip()] = annotation.strip()
    return result


def find_bare_int_path_params() -> list[str]:
    """返回违规报告行：注解为 int 但路径仍是裸 {name}。"""
    violations: list[str] = []
    for py in sorted(ROOT.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        text = py.read_text(encoding="utf-8")
        rel = py.relative_to(ROOT.parents[1]).as_posix()
        for match in DECORATOR_RE.finditer(text):
            path = match.group(3)
            line = text[: match.start()].count("\n") + 1
            annotations = _func_annotations(text, match.end())
            for param_match in PARAM_RE.finditer(path):
                name, converter = param_match.group(1), param_match.group(2)
                if converter is not None:
                    continue
                if annotations.get(name) == "int":
                    violations.append(
                        f"{rel}:{line}  path={path}  {{{name}}} annotated int "
                        f"but missing :int converter"
                    )
    return violations


def main() -> int:
    violations = find_bare_int_path_params()
    if not violations:
        print("ok: no bare int path params under app/routers")
        return 0
    print("FAIL (zero exceptions): int path params must be /{name:int}; bare /{name} is forbidden:")
    for line in violations:
        print(f"  {line}")
    print("Rule: .cursor/rules/api-type-safety.mdc §6 — do not merge until fixed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
