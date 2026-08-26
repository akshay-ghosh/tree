#!/usr/bin/env python3
"""Entry point for the `tree` command: prints a boxed or indented diagram of a directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import ast_scope
import render_boxed
import render_indented
import render_pdf
from config import load_config
from scanner import build_tree


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="tree", description="Print a diagram of a directory's structure.")
    parser.add_argument("path", nargs="?", default=".", help="directory to scan (default: current directory)")
    parser.add_argument("--style", choices=["boxed", "indented"], default=None, help="rendering style")
    parser.add_argument("--scope", choices=["files", "code"], default=None, help="node scope")
    parser.add_argument("-d", "--depth", type=int, default=None, help="max directory depth")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI color output")
    parser.add_argument("--all", action="store_true", help="ignore .gitignore and show hidden files")
    parser.add_argument("-s", "--save", action="store_true", help="save the diagram as a PDF instead of printing")
    parser.add_argument(
        "-p",
        "--print",
        action="store_true",
        dest="print_flag",
        help="also print to the terminal when saving (printing already happens by default without --save)",
    )
    return parser.parse_args(argv)


def _attach_code_scope(node, max_depth: int | None) -> None:
    if node.kind == "file" and node.path.suffix == ".py" and (max_depth is None or node.depth < max_depth):
        node.children = ast_scope.extract_python_members(node.path, node.depth + 1)
    for child in node.children:
        _attach_code_scope(child, max_depth)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    config = load_config()

    style = args.style or config["style"]
    scope = args.scope or config["scope"]
    save = args.save
    print_enabled = args.print_flag or not save
    depth = args.depth if args.depth is not None else (None if save else config["max_depth"])
    color_enabled = config["color"] and not args.no_color
    respect_gitignore = config["respect_gitignore"] and not args.all
    show_hidden = config["show_hidden"] or args.all

    root_path = Path(args.path).resolve()
    if not root_path.is_dir():
        print(f"tree: not a directory: {args.path}", file=sys.stderr)
        return 1

    try:
        tree = build_tree(
            root_path,
            max_depth=depth,
            respect_gitignore=respect_gitignore,
            show_hidden=show_hidden,
            always_skip=config["always_skip"],
        )

        if scope == "code":
            _attach_code_scope(tree, depth)

        if print_enabled:
            if style == "boxed":
                output = render_boxed.render(tree, color_enabled=color_enabled, config=config)
            else:
                output = render_indented.render(tree, color_enabled=color_enabled, config=config)
            print(output)

        if save:
            pdf_path = Path.cwd() / f"{root_path.name}_tree.pdf"
            render_pdf.save(tree, pdf_path, style=style, color_enabled=color_enabled, config=config)
            print(f"Saved to {pdf_path}")

        return 0
    except Exception as e:  # personal CLI tool: one friendly failure mode is enough
        print(f"tree: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
