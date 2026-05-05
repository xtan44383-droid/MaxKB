#!/usr/bin/env bash
# 本地源码启动 MaxKB Web（需已启动 Docker 中的 Postgres/Redis，且 config.yml 端口一致）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p data/hf data/embedding tmp
exec "$ROOT/.venv/bin/python" main.py dev web
