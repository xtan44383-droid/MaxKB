#!/usr/bin/env bash
# 一条命令完成：依赖安装 + admin/chat 打包 + collectstatic（改 ui 后看 8080 集成效果用）
# 使用场景：只跑 python main.py dev web 时，浏览器读的是 apps/static，必须先更新 ui/dist 并收集静态文件。

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/ui"

# Vite 6 需要 Node 20+；若报 await / Unexpected reserved word，请先升级 Node（见 docs 09）
NODE_MAJOR=$(node -p "parseInt(process.versions.node.split('.')[0],10)" 2>/dev/null || echo 0)
if [[ "${NODE_MAJOR}" -lt 20 ]]; then
  echo "错误: 当前 Node 为 $(node -v 2>/dev/null || echo 未知)，需要 >= 20（见 ui/.nvmrc）。"
  echo "示例: nvm install 20 && nvm use 20"
  exit 1
fi

# Vite 打大包时默认 ~2GB 堆容易 OOM；加大上限（仍失败可先 export NODE_OPTIONS=--max-old-space-size=12288 再跑脚本）
export NODE_OPTIONS="--max-old-space-size=8192"

echo ">>> npm install（保证依赖齐全，首次会稍慢）..."
npm install --no-fund --no-audit

echo ">>> 构建管理端 (admin)..."
npm run build-only

echo ">>> 构建对话端 (chat)..."
npm run build-only-chat

cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

echo ">>> collectstatic（写入 apps/static）..."
"$PY" main.py collect_static

echo "完成。请在本机：① 重启 Web ② 浏览器 Ctrl+Shift+R 强刷。（AI 无法替你点浏览器或关你别的终端里的进程。）"
