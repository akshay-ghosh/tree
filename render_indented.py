"""Classic indented tree renderer (like the standard `tree` CLI)."""

from __future__ import annotations

from colors import color_for, colorize


def _label(node) -> str:
    return node.name + "/" if node.kind == "dir" else node.name


def iter_rows(node, prefix: str = "", is_last: bool = True, is_root: bool = True):
    """Yields (prefix_including_connector, node) for every node in display order."""
    yield ("" if is_root else prefix + ("└── " if is_last else "├── ")), node
    children = node.children
    child_prefix = prefix if is_root else prefix + ("    " if is_last else "│   ")
    for i, child in enumerate(children):
        yield from iter_rows(child, child_prefix, i == len(children) - 1, False)


def render(root, *, color_enabled: bool, config: dict) -> str:
    lines = [
        prefix + colorize(_label(node), color_for(node, config), color_enabled) for prefix, node in iter_rows(root)
    ]
    return "\n".join(lines)
