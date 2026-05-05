#!/usr/bin/env bash
# 纯 Linux 内部目录启动 Web
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export HF_HOME="${HF_HOME:-$ROOT/data/hf}"
export TMPDIR="${TMPDIR:-$ROOT/tmp}"
mkdir -p data/hf data/embedding tmp
source "$ROOT/.venv/bin/activate"
exec python main.py dev web
