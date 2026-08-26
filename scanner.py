"""Walks a filesystem path into a Node tree, applying gitignore/depth/hidden filtering."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pathspec


@dataclass
class Node:
    name: str
    path: Path
    is_dir: bool
    kind: str = "file"  # "dir" | "file" | "function" | "class" | "import" | "error"
    depth: int = 0
    children: list["Node"] = field(default_factory=list)


def _load_gitignore(dir_path: Path) -> pathspec.PathSpec | None:
    gitignore = dir_path / ".gitignore"
    if not gitignore.is_file():
        return None
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def _is_ignored(path: Path, is_dir: bool, specs: list[tuple[Path, pathspec.PathSpec]]) -> bool:
    for base_dir, spec in specs:
        rel = path.relative_to(base_dir).as_posix()
        if is_dir:
            rel += "/"
        if spec.match_file(rel):
            return True
    return False


def _scan_dir(
    dir_path: Path,
    depth: int,
    *,
    max_depth: int | None,
    respect_gitignore: bool,
    show_hidden: bool,
    always_skip: set[str],
    specs: list[tuple[Path, pathspec.PathSpec]],
) -> list[Node]:
    if respect_gitignore:
        local_spec = _load_gitignore(dir_path)
        if local_spec is not None:
            specs = specs + [(dir_path, local_spec)]

    try:
        entries = list(dir_path.iterdir())
    except OSError:
        return []

    entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))

    children: list[Node] = []
    for entry in entries:
        if entry.name in always_skip:
            continue
        if not show_hidden and entry.name.startswith("."):
            continue

        is_dir = entry.is_dir()
        if respect_gitignore and _is_ignored(entry, is_dir, specs):
            continue

        node = Node(name=entry.name, path=entry, is_dir=is_dir, kind="dir" if is_dir else "file", depth=depth)
        if is_dir and (max_depth is None or depth < max_depth):
            node.children = _scan_dir(
                entry,
                depth + 1,
                max_depth=max_depth,
                respect_gitignore=respect_gitignore,
                show_hidden=show_hidden,
                always_skip=always_skip,
                specs=specs,
            )
        children.append(node)

    return children


def build_tree(
    root: Path,
    *,
    max_depth: int | None,
    respect_gitignore: bool,
    show_hidden: bool,
    always_skip: list[str],
) -> Node:
    skip_set = set(always_skip)
    root_node = Node(name=root.name or str(root), path=root, is_dir=True, kind="dir", depth=0)
    if max_depth is None or max_depth >= 1:
        root_node.children = _scan_dir(
            root,
            1,
            max_depth=max_depth,
            respect_gitignore=respect_gitignore,
            show_hidden=show_hidden,
            always_skip=skip_set,
            specs=[],
        )
    return root_node
