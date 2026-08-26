#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZSHRC="$HOME/.zshrc"
MARKER_START="# >>> tree_command >>>"
MARKER_END="# <<< tree_command <<<"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found -- install it first (e.g. 'brew install python3') and re-run this script." >&2
    exit 1
fi

echo "Setting up tree_command in $SCRIPT_DIR ..."
python3 -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"

if grep -qF "$MARKER_START" "$ZSHRC" 2>/dev/null; then
    echo "tree() already present in $ZSHRC -- leaving it untouched."
else
    {
        echo ""
        echo "$MARKER_START"
        echo "tree() {"
        echo "    \"$SCRIPT_DIR/.venv/bin/python3\" \"$SCRIPT_DIR/main.py\" \"\$@\""
        echo "}"
        echo "$MARKER_END"
    } >> "$ZSHRC"
    echo "Added tree() to $ZSHRC"
fi

echo "Done. Run 'source ~/.zshrc' (or open a new terminal), then just type: tree"
