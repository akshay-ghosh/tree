"""Classic indented tree renderer (like the standard `tree` CLI)."""

from __future__ import annotations

from colors import color_for, colorize


def _label(node) -> str:
    return node.name + "/" if node.kind == "dir" else node.name


def render(root, *, color_enabled: bool, config: dict) -> str:
    lines: list[str] = [colorize(_label(root), color_for(root, config), color_enabled)]
    _render_children(root, "", lines, color_enabled=color_enabled, config=config)
    return "\n".join(lines)


def _render_children(node, prefix: str, lines: list[str], *, color_enabled: bool, config: dict) -> None:
    children = node.children
    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        connector = "└── " if is_last else "├── "
        lines.append(prefix + connector + colorize(_label(child), color_for(child, config), color_enabled))
        child_prefix = prefix + ("    " if is_last else "│   ")
        _render_children(child, child_prefix, lines, color_enabled=color_enabled, config=config)
