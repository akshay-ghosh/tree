# tree

A `tree` command that prints a diagram of a directory's structure — either
a left-to-right boxed node diagram (default) or a classic indented tree —
and can export it as a high-resolution vector PDF for repos too large to
fit on screen.

## Setup on a new machine

```bash
git clone git@github.com:akshay-ghosh/tree.git tree_command
cd tree_command
git checkout feature/save_pdf_arg
./setup.sh
source ~/.zshrc
```

`setup.sh` creates a `.venv`, installs dependencies, and appends a `tree()`
function to `~/.zshrc` (safe to re-run — it won't add a duplicate). After
that, just run `tree` from any directory.

## Usage

```
tree [path] [--style boxed|indented] [--scope files|code] [-d N]
     [--no-color] [--all] [-s|--save] [-p|--print]
```

- `--style boxed|indented` — box diagram (default) or classic `├──` tree.
- `--scope files|code` — plain file/folder hierarchy (default), or also
  show each `.py` file's top-level functions/classes/imports.
- `-d N` — cap directory depth (default: 3 when printing).
- `--no-color` — disable color output.
- `--all` — ignore `.gitignore` and show hidden files.
- `-s`, `--save` — save the diagram as a PDF (`<dirname>_tree.pdf` in the
  current directory) instead of printing. Uses full depth by default
  unless `-d` is given. Combine with `-p` to also print to the terminal.

Defaults (style, scope, depth, colors, gitignore handling) live in
`config.yaml`, loaded relative to this script regardless of which
directory you run `tree` from.
