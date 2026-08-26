"""Saves the node diagram as a vector PDF (boxes/lines/text, no rasterization).

Mirrors the two-pass layout algorithm in render_boxed.py (depth-grouped
columns sharing a bus line per depth; bottom-up subtree-height then
top-down centering for rows) but expressed natively in PDF points instead
of character-grid units, since the constants that read well as monospace
text aren't the constants that read well as padded vector boxes. Kept as a
deliberate copy-and-adapt rather than a shared abstraction -- the two
renderers have different unit systems and there are only two call sites.

Text uses the base-14 Courier font (no embedding required); filenames with
characters outside Latin-1/WinAnsi won't render correctly -- an accepted
limitation for a personal tool. Labels are colored by the same category
logic (colors.color_for) used for terminal output, but remapped to a
separate print-safe palette below -- the terminal's ANSI palette is tuned
for a dark background (e.g. yellow/white) and would be largely illegible
on a white page. Box borders and connector lines stay black regardless,
matching the terminal renderer's choice to color label text only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors as rl_colors
from reportlab.pdfgen import canvas

from colors import color_for
from render_boxed import _all_nodes, _label
from render_indented import iter_rows

# Same category names colors.color_for() resolves to (directory/python/
# markdown/config/function/class/import/default, plus the hardcoded "red"
# for parse errors), remapped to colors that hold contrast on white paper.
PDF_PALETTE = {
    "blue": rl_colors.HexColor("#1c4fd6"),
    "green": rl_colors.HexColor("#1a7a1a"),
    "yellow": rl_colors.HexColor("#8a6d00"),
    "magenta": rl_colors.HexColor("#8a1a8a"),
    "cyan": rl_colors.HexColor("#00787a"),
    "white": rl_colors.black,
    "dim": rl_colors.HexColor("#666666"),
    "red": rl_colors.HexColor("#b00000"),
    "default": rl_colors.black,
}


def _pdf_color(node, config: dict):
    return PDF_PALETTE.get(color_for(node, config), rl_colors.black)

FONT_SIZE = 9
CHAR_W_PT = FONT_SIZE * 0.6  # Courier advance width is exactly 0.6em
PAD_PT = 8
BOX_HEIGHT_PT = 22
VGAP_PT = 6
STEM_GAP_PT = 16
LEAF_GAP_PT = 16
MARGIN_PT = 20

INDENT_LINE_HEIGHT_PT = FONT_SIZE * 1.4

# Courier (base-14 PDF font, WinAnsiEncoding) has no glyphs for these
# box-drawing characters -- they'd render as missing-glyph boxes. Swap in
# ASCII equivalents for the PDF-only indented output.
_ASCII_CONNECTORS = str.maketrans({"├": "|", "└": "`", "│": "|", "─": "-"})


@dataclass
class _Layout:
    center_y: float = 0.0
    left_x: float = 0.0
    width: float = 0.0


def _box_width_pt(node) -> float:
    return len(_label(node)) * CHAR_W_PT + 2 * PAD_PT


def _compute_columns(root) -> tuple[dict[int, float], dict[int, float], int]:
    by_depth: dict[int, list] = {}
    for node in _all_nodes(root):
        by_depth.setdefault(node.depth, []).append(node)

    max_depth = max(by_depth)
    col_width = {d: max(_box_width_pt(n) for n in nodes) for d, nodes in by_depth.items()}

    col_x: dict[int, float] = {0: 0.0}
    bus_x: dict[int, float] = {}
    for d in range(max_depth + 1):
        bus_x[d] = col_x[d] + col_width[d] + STEM_GAP_PT
        col_x[d + 1] = bus_x[d] + LEAF_GAP_PT

    return col_x, bus_x, max_depth


def _subtree_height(node, heights: dict[int, float]) -> float:
    if not node.children:
        h = BOX_HEIGHT_PT
    else:
        children_total = sum(_subtree_height(c, heights) for c in node.children) + VGAP_PT * (
            len(node.children) - 1
        )
        h = max(BOX_HEIGHT_PT, children_total)
    heights[id(node)] = h
    return h


def _place(node, y0: float, col_x: dict[int, float], heights: dict[int, float], layout: dict[int, _Layout]) -> None:
    h = heights[id(node)]
    bw = _box_width_pt(node)
    center_y = y0 + h / 2
    layout[id(node)] = _Layout(center_y=center_y, left_x=col_x[node.depth], width=bw)

    if node.children:
        children_total = sum(heights[id(c)] for c in node.children) + VGAP_PT * (len(node.children) - 1)
        cursor = y0 + (h - children_total) / 2
        for child in node.children:
            _place(child, cursor, col_x, heights, layout)
            cursor += heights[id(child)] + VGAP_PT


def _save_boxed(root, path: Path, *, color_enabled: bool, config: dict) -> None:
    col_x, bus_x, max_depth = _compute_columns(root)

    heights: dict[int, float] = {}
    _subtree_height(root, heights)

    layout: dict[int, _Layout] = {}
    _place(root, 0.0, col_x, heights, layout)

    total_height = heights[id(root)]
    total_width = col_x[max_depth] + max(
        layout[id(n)].width for n in _all_nodes(root) if n.depth == max_depth
    )

    page_w = total_width + 2 * MARGIN_PT
    page_h = total_height + 2 * MARGIN_PT

    def to_pdf_y(grid_y: float) -> float:
        return page_h - MARGIN_PT - grid_y

    c = canvas.Canvas(str(path), pagesize=(page_w, page_h))
    c.setFont("Courier", FONT_SIZE)
    c.setLineWidth(1)
    c.setStrokeColor(rl_colors.black)

    for node in _all_nodes(root):
        info = layout[id(node)]
        x = MARGIN_PT + info.left_x
        top_pdf = to_pdf_y(info.center_y - BOX_HEIGHT_PT / 2)
        bottom_pdf = top_pdf - BOX_HEIGHT_PT

        c.rect(x, bottom_pdf, info.width, BOX_HEIGHT_PT)
        c.setFillColor(_pdf_color(node, config) if color_enabled else rl_colors.black)
        c.drawString(x + PAD_PT, bottom_pdf + BOX_HEIGHT_PT / 2 - FONT_SIZE * 0.35, _label(node))

        if node.children:
            bx = MARGIN_PT + bus_x[node.depth]
            parent_y_pdf = to_pdf_y(info.center_y)
            c.line(x + info.width, parent_y_pdf, bx, parent_y_pdf)

            child_centers = [layout[id(c2)].center_y for c2 in node.children]
            c.line(bx, to_pdf_y(min(child_centers)), bx, to_pdf_y(max(child_centers)))

            for child in node.children:
                c_info = layout[id(child)]
                cy_pdf = to_pdf_y(c_info.center_y)
                c.line(bx, cy_pdf, MARGIN_PT + c_info.left_x, cy_pdf)

    c.save()


def _save_indented(root, path: Path, *, color_enabled: bool, config: dict) -> None:
    rows = [
        (prefix.translate(_ASCII_CONNECTORS), _label(node), node) for prefix, node in iter_rows(root)
    ]

    max_len = max((len(prefix) + len(label) for prefix, label, _ in rows), default=1)
    page_w = max_len * CHAR_W_PT + 2 * MARGIN_PT
    page_h = len(rows) * INDENT_LINE_HEIGHT_PT + 2 * MARGIN_PT

    c = canvas.Canvas(str(path), pagesize=(page_w, page_h))
    c.setFont("Courier", FONT_SIZE)
    c.setFillColor(rl_colors.black)

    y = page_h - MARGIN_PT - FONT_SIZE
    for prefix, label, node in rows:
        c.setFillColor(rl_colors.black)
        c.drawString(MARGIN_PT, y, prefix)
        c.setFillColor(_pdf_color(node, config) if color_enabled else rl_colors.black)
        c.drawString(MARGIN_PT + len(prefix) * CHAR_W_PT, y, label)
        y -= INDENT_LINE_HEIGHT_PT

    c.save()


def save(root, path: Path, *, style: str, color_enabled: bool, config: dict) -> None:
    if style == "indented":
        _save_indented(root, path, color_enabled=color_enabled, config=config)
    else:
        _save_boxed(root, path, color_enabled=color_enabled, config=config)
