#!/usr/bin/env bash
# Repeatable installation; leaves source and the lockfile unchanged.
set -euo pipefail
BCI_REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BCI_REPO_DIR"
command -v uv >/dev/null
if [[ "$BCI_REPO_DIR" == /workspace/* ]]; then
    BCI_DEFAULT_ENV=/workspace/.venvs/few-shot-mi-eeg
    BCI_DEFAULT_TOOLS=/workspace/.bci-tools
    BCI_DEFAULT_CACHE=/workspace/.cache/uv
else
    BCI_DEFAULT_ENV="$BCI_REPO_DIR/.venv"
    BCI_DEFAULT_TOOLS="$BCI_REPO_DIR/.cache/tools"
    BCI_DEFAULT_CACHE="$BCI_REPO_DIR/.cache/uv"
fi
export UV_CACHE_DIR="${UV_CACHE_DIR:-$BCI_DEFAULT_CACHE}"
export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$BCI_DEFAULT_TOOLS/python}"
export UV_PYTHON_BIN_DIR="${UV_PYTHON_BIN_DIR:-$BCI_DEFAULT_TOOLS/bin}"
export UV_PROJECT_ENVIRONMENT="${BCI_ENV_DIR:-${UV_PROJECT_ENVIRONMENT:-$BCI_DEFAULT_ENV}}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$(dirname "$UV_CACHE_DIR")}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$XDG_CACHE_HOME/matplotlib}"
mkdir -p "$MPLCONFIGDIR"
uv python install 3.11.16
uv sync --locked --all-extras
uv pip check --python "$UV_PROJECT_ENVIRONMENT/bin/python"
"$UV_PROJECT_ENVIRONMENT/bin/python" -c 'import learning_preserving_bci; print("Installed", learning_preserving_bci.__version__)'
