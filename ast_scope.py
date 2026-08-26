"""Extracts top-level functions/classes/imports from a Python file as Node children."""

from __future__ import annotations

import ast
from pathlib import Path

from scanner import Node

_MAX_LABEL_LEN = 60


def _truncate(text: str) -> str:
    if len(text) <= _MAX_LABEL_LEN:
        return text
    return text[: _MAX_LABEL_LEN - 1] + "…"


def extract_python_members(file_path: Path, depth: int) -> list[Node]:
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))
    except (OSError, SyntaxError):
        return [Node(name="<unparsable>", path=file_path, is_dir=False, kind="error", depth=depth)]

    members: list[Node] = []
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(stmt, ast.AsyncFunctionDef) else "def"
            members.append(
                Node(name=f"{prefix} {stmt.name}()", path=file_path, is_dir=False, kind="function", depth=depth)
            )
        elif isinstance(stmt, ast.ClassDef):
            members.append(
                Node(name=f"class {stmt.name}", path=file_path, is_dir=False, kind="class", depth=depth)
            )
        elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
            members.append(
                Node(name=_truncate(ast.unparse(stmt)), path=file_path, is_dir=False, kind="import", depth=depth)
            )

    return members
