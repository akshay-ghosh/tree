"""Org-chart style box diagram renderer.

Two-pass layout:
  1. Bottom-up: each node is given a subtree width = max(its own box width,
     sum of its children's subtree widths + gaps). This guarantees sibling
     subtrees never overlap.
  2. Top-down: each node is handed a column span and centered within it;
     centering the parent over its children falls out automatically because
     both are derived from the same span.

Then the tree is drawn onto a plain-text 2D character canvas, layer by
layer, with a 3-row connector block (stem / bus / stems) between levels.
"""

from __future__ import annotations

from dataclasses import dataclass

from colors import ANSI, color_for

GAP = 2
BOX_ROWS = 3
CONNECTOR_ROWS = 3
LEVEL_ROWS = BOX_ROWS + CONNECTOR_ROWS


@dataclass
class _Layout:
    center_x: int = 0
    left_x: int = 0
    width: int = 0


def _label(node) -> str:
    return node.name + "/" if node.kind == "dir" else node.name


def _box_width(node) -> int:
    return len(_label(node)) + 4


def _compute_subtree_widths(node, widths: dict[int, int]) -> int:
    if not node.children:
        w = _box_width(node)
    else:
        children_total = sum(_compute_subtree_widths(c, widths) for c in node.children) + GAP * (
            len(node.children) - 1
        )
        w = max(_box_width(node), children_total)
    widths[id(node)] = w
    return w


def _place(node, x0: int, widths: dict[int, int], layout: dict[int, _Layout]) -> None:
    w = widths[id(node)]
    bw = _box_width(node)
    center = x0 + w // 2
    left = center - bw // 2
    layout[id(node)] = _Layout(center_x=center, left_x=left, width=bw)

    if node.children:
        children_total = sum(widths[id(c)] for c in node.children) + GAP * (len(node.children) - 1)
        cursor = x0 + (w - children_total) // 2
        for child in node.children:
            _place(child, cursor, widths, layout)
            cursor += widths[id(child)] + GAP


def _tree_height(node) -> int:
    if not node.children:
        return 0
    return 1 + max(_tree_height(c) for c in node.children)


def _write_label(canvas: list[list[str]], row: int, col_start: int, label: str, color_name: str, color_enabled: bool) -> None:
    n = len(label)
    for i, ch in enumerate(label):
        cell = ch
        if color_enabled:
            code = ANSI.get(color_name, "")
            if n == 1:
                cell = f"{code}{ch}{ANSI['reset']}"
            elif i == 0:
                cell = f"{code}{ch}"
            elif i == n - 1:
                cell = f"{ch}{ANSI['reset']}"
        canvas[row][col_start + i] = cell


def _draw_box(node, layout: dict[int, _Layout], canvas: list[list[str]], *, color_enabled: bool, config: dict) -> None:
    info = layout[id(node)]
    row0 = node.depth * LEVEL_ROWS
    left = info.left_x
    bw = info.width

    canvas[row0][left] = "┌"
    canvas[row0][left + bw - 1] = "┐"
    for c in range(left + 1, left + bw - 1):
        canvas[row0][c] = "─"

    canvas[row0 + 2][left] = "└"
    canvas[row0 + 2][left + bw - 1] = "┘"
    for c in range(left + 1, left + bw - 1):
        canvas[row0 + 2][c] = "─"

    canvas[row0 + 1][left] = "│"
    canvas[row0 + 1][left + bw - 1] = "│"
    label = _label(node)
    _write_label(canvas, row0 + 1, left + 2, label, color_for(node, config), color_enabled)


def _draw_connectors(node, layout: dict[int, _Layout], canvas: list[list[str]]) -> None:
    if not node.children:
        return

    row0 = node.depth * LEVEL_ROWS
    parent_center = layout[id(node)].center_x
    child_centers = [layout[id(c)].center_x for c in node.children]

    stem_row = row0 + BOX_ROWS
    bus_row = row0 + BOX_ROWS + 1
    leaf_row = row0 + BOX_ROWS + 2

    canvas[stem_row][parent_center] = "│"

    left_ext = min(child_centers + [parent_center])
    right_ext = max(child_centers + [parent_center])
    for col in range(left_ext, right_ext + 1):
        canvas[bus_row][col] = "─"

    for col in child_centers:
        canvas[bus_row][col] = "┼" if col == parent_center else "┬"
    if parent_center not in child_centers:
        canvas[bus_row][parent_center] = "┴"

    if len(child_centers) > 1:
        leftmost, rightmost = min(child_centers), max(child_centers)
        if canvas[bus_row][leftmost] == "┬":
            canvas[bus_row][leftmost] = "┌"
        if canvas[bus_row][rightmost] == "┬":
            canvas[bus_row][rightmost] = "┐"

    for col in child_centers:
        canvas[leaf_row][col] = "│"


def render(root, *, color_enabled: bool, config: dict) -> str:
    widths: dict[int, int] = {}
    _compute_subtree_widths(root, widths)

    layout: dict[int, _Layout] = {}
    _place(root, 0, widths, layout)

    height = _tree_height(root)
    total_rows = (height + 1) * BOX_ROWS + height * CONNECTOR_ROWS
    total_cols = widths[id(root)]

    canvas = [[" " for _ in range(total_cols)] for _ in range(total_rows)]

    stack = [root]
    while stack:
        node = stack.pop()
        _draw_box(node, layout, canvas, color_enabled=color_enabled, config=config)
        _draw_connectors(node, layout, canvas)
        stack.extend(node.children)

    lines = ["".join(row).rstrip() for row in canvas]
    return "\n".join(lines)
