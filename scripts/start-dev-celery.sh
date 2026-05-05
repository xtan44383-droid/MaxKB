#!/usr/bin/env bash
# 本地启动 Celery Worker（知识库向量化、异步任务依赖此进程）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec "$ROOT/.venv/bin/python" main.py dev celery
