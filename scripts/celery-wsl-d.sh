#!/usr/bin/env bash
# 在 WSL 中启动 Celery（与 dev-wsl-d.sh 同目录、同 venv，物理在 D 盘）
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export HF_HOME="${HF_HOME:-$ROOT/data/hf}"
export TMPDIR="${TMPDIR:-$ROOT/tmp}"
mkdir -p data/hf data/embedding tmp
# shellcheck source=/dev/null
source "$ROOT/.venv-wsl/bin/activate"
exec python main.py dev celery
