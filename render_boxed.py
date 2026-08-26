"""Left-to-right org-chart box diagram renderer.

Root box on the left; children stack vertically to its right; grandchildren
further right still. Width scales with tree depth (capped by max_depth),
height scales with node count -- terminals handle extra height via normal
scrolling far better than extra width, which is why this is rotated 90
degrees from a top-down fan-out.

Two independent layout passes, one per axis:

  X (column): grouped by depth, not recursive. Every node at depth d
  left-aligns at col_x[d]; a fixed bus column bus_x[d] sits a couple of
  dash-columns to the right of the widest box at that depth, and the next
  column starts a couple of dash-columns past the bus. Because bus_x only
  depends on depth, multiple parents at the same depth safely share one bus
  column -- their row ranges never overlap by construction (see Y below).

  Y (row): bottom-up subtree-height, then top-down centering -- the same
  "reserve full subtree extent, then center within it" trick the original
  top-down renderer used on columns, just applied to rows instead. This
  guarantees sibling subtrees never overlap vertically and a parent's box
  falls out vertically centered over its children's block for free.

Connectors are drawn at each parent's bus column by computing, per row, the
set of directions (up/down/left/right) that column needs to show, and
looking up the matching box-drawing glyph from a fixed table.
"""

from __future__ import annotations

from dataclasses import dataclass

from colors import ANSI, color_for

BOX_ROWS = 3
VGAP = 0
STEM_DASHES = 2
LEAF_DASHES = 2

_GLYPH = {
    frozenset(): " ",
    frozenset({"up", "down"}): "│",
    frozenset({"left", "right"}): "─",
    frozenset({"left"}): "─",
    frozenset({"right"}): "─",
    frozenset({"up"}): "│",
    frozenset({"down"}): "│",
    frozenset({"down", "right"}): "┌",
    frozenset({"down", "left"}): "┐",
    frozenset({"up", "right"}): "└",
    frozenset({"up", "left"}): "┘",
    frozenset({"up", "down", "right"}): "├",
    frozenset({"up", "down", "left"}): "┤",
    frozenset({"left", "right", "down"}): "┬",
    frozenset({"left", "right", "up"}): "┴",
    frozenset({"up", "down", "left", "right"}): "┼",
}


@dataclass
class _Layout:
    center_y: int = 0
    left_x: int = 0
    width: int = 0


def _label(node) -> str:
    return node.name + "/" if node.kind == "dir" else node.name


def _box_width(node) -> int:
    return len(_label(node)) + 4


def _all_nodes(root):
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.children)


def _compute_columns(root) -> tuple[dict[int, int], dict[int, int]]:
    by_depth: dict[int, list] = {}
    for node in _all_nodes(root):
        by_depth.setdefault(node.depth, []).append(node)

    max_depth = max(by_depth)
    col_width = {d: max(_box_width(n) for n in nodes) for d, nodes in by_depth.items()}

    col_x: dict[int, int] = {0: 0}
    bus_x: dict[int, int] = {}
    for d in range(max_depth + 1):
        bus_x[d] = col_x[d] + col_width[d] + STEM_DASHES
        col_x[d + 1] = bus_x[d] + 1 + LEAF_DASHES

    return col_x, bus_x


def _subtree_height(node, heights: dict[int, int]) -> int:
    if not node.children:
        h = BOX_ROWS
    else:
        children_total = sum(_subtree_height(c, heights) for c in node.children) + VGAP * (
            len(node.children) - 1
        )
        h = max(BOX_ROWS, children_total)
    heights[id(node)] = h
    return h


def _place(node, y0: int, col_x: dict[int, int], heights: dict[int, int], layout: dict[int, _Layout]) -> None:
    h = heights[id(node)]
    bw = _box_width(node)
    center_y = y0 + h // 2
    layout[id(node)] = _Layout(center_y=center_y, left_x=col_x[node.depth], width=bw)

    if node.children:
        children_total = sum(heights[id(c)] for c in node.children) + VGAP * (len(node.children) - 1)
        cursor = y0 + (h - children_total) // 2
        for child in node.children:
            _place(child, cursor, col_x, heights, layout)
            cursor += heights[id(child)] + VGAP


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
    left = info.left_x
    bw = info.width
    top = info.center_y - 1

    canvas[top][left] = "┌"
    canvas[top][left + bw - 1] = "┐"
    for c in range(left + 1, left + bw - 1):
        canvas[top][c] = "─"

    canvas[top + 2][left] = "└"
    canvas[top + 2][left + bw - 1] = "┘"
    for c in range(left + 1, left + bw - 1):
        canvas[top + 2][c] = "─"

    canvas[top + 1][left] = "│"
    canvas[top + 1][left + bw - 1] = "│"
    _write_label(canvas, top + 1, left + 2, _label(node), color_for(node, config), color_enabled)


def _draw_connectors(node, layout: dict[int, _Layout], bus_x: dict[int, int], canvas: list[list[str]]) -> None:
    if not node.children:
        return

    info = layout[id(node)]
    bx = bus_x[node.depth]
    parent_row = info.center_y
    child_rows = [layout[id(c)].center_y for c in node.children]

    canvas[parent_row][info.left_x + info.width] = "─"
    for c in range(info.left_x + info.width + 1, bx):
        canvas[parent_row][c] = "─"

    top_row, bottom_row = min(child_rows), max(child_rows)
    child_row_set = set(child_rows)
    for row in range(top_row, bottom_row + 1):
        flags = set()
        if row > top_row:
            flags.add("up")
        if row < bottom_row:
            flags.add("down")
        if row in child_row_set:
            flags.add("right")
        if row == parent_row:
            flags.add("left")
        canvas[row][bx] = _GLYPH[frozenset(flags)]

    for child in node.children:
        child_info = layout[id(child)]
        row = child_info.center_y
        for c in range(bx + 1, child_info.left_x):
            canvas[row][c] = "─"


def render(root, *, color_enabled: bool, config: dict) -> str:
    col_x, bus_x = _compute_columns(root)

    heights: dict[int, int] = {}
    _subtree_height(root, heights)

    layout: dict[int, _Layout] = {}
    _place(root, 0, col_x, heights, layout)

    total_rows = heights[id(root)]
    max_depth = max(node.depth for node in _all_nodes(root))
    total_cols = col_x[max_depth] + max(
        layout[id(n)].width for n in _all_nodes(root) if n.depth == max_depth
    )

    canvas = [[" " for _ in range(total_cols)] for _ in range(total_rows)]

    for node in _all_nodes(root):
        _draw_box(node, layout, canvas, color_enabled=color_enabled, config=config)
        _draw_connectors(node, layout, bus_x, canvas)

    lines = ["".join(row).rstrip() for row in canvas]
    return "\n".join(lines)
