"""ANSI color table and node -> color resolution."""

from __future__ import annotations

ANSI = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}

_CONFIG_SUFFIXES = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"}


def color_for(node, config: dict) -> str:
    colors = config.get("colors", {})

    if node.kind == "dir":
        return colors.get("directory", "default")
    if node.kind in ("function", "class", "import"):
        return colors.get(node.kind, "default")
    if node.kind == "error":
        return "red"

    suffix = node.path.suffix.lower()
    if suffix == ".py":
        return colors.get("python", "default")
    if suffix == ".md":
        return colors.get("markdown", "default")
    if suffix in _CONFIG_SUFFIXES:
        return colors.get("config", "default")
    return colors.get("default", "default")


def colorize(text: str, color_name: str, enabled: bool) -> str:
    if not enabled:
        return text
    code = ANSI.get(color_name)
    if not code:
        return text
    return f"{code}{text}{ANSI['reset']}"
