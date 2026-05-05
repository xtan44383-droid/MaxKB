#!/usr/bin/env bash
# 在 WSL 终端中启动 MaxKB Web 开发服务（需已安装 .venv-wsl 与 Docker 中的 PG/Redis）
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p data/hf data/embedding tmp
export HF_HOME="${HF_HOME:-$ROOT/data/hf}"
export TMPDIR="${TMPDIR:-$ROOT/tmp}"
# shellcheck source=/dev/null
source "$ROOT/.venv-wsl/bin/activate"
exec python main.py dev web
