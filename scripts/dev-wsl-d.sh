#!/usr/bin/env bash
# MaxKB 在 WSL 中开发：代码与 .venv 均在 D 盘本仓库（/mnt/d/...），勿再复制到 ~
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export HF_HOME="${HF_HOME:-$ROOT/data/hf}"
export TMPDIR="${TMPDIR:-$ROOT/tmp}"
mkdir -p data/hf data/embedding tmp
# shellcheck source=/dev/null
source "$ROOT/.venv-wsl/bin/activate"
exec python main.py dev web
