"""Loads config.yaml relative to this script's own location."""

from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

DEFAULTS: dict = {
    "style": "boxed",
    "scope": "files",
    "max_depth": 3,
    "color": True,
    "respect_gitignore": True,
    "show_hidden": False,
    "always_skip": [".git"],
    "colors": {
        "directory": "blue",
        "python": "green",
        "markdown": "yellow",
        "config": "magenta",
        "function": "cyan",
        "class": "magenta",
        "import": "dim",
        "default": "white",
    },
}


def load_config() -> dict:
    merged = {**DEFAULTS}
    try:
        loaded = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    except (OSError, yaml.YAMLError):
        loaded = {}

    merged.update({k: v for k, v in loaded.items() if k != "colors"})
    if "colors" in loaded and isinstance(loaded["colors"], dict):
        merged["colors"] = {**DEFAULTS["colors"], **loaded["colors"]}

    return merged
