---
name: maxkb-ui-build-static
description: >-
  Builds MaxKB admin and chat UIs into Django static assets after source changes under ui/.
  Use when the user edits Vue/TS in ui/, asks to see UI changes on port 8080, mentions
  build-ui-static, collectstatic, or "改完前端看不到效果".
---

# MaxKB 前端静态构建与验收

## 事实

本仓库日常是 Django `main.py dev web` 提供 8080，浏览器拿到的是已打包进 `apps/static` 的静态文件，不是 Vite 热更内存。改 `ui/` 源码后必须重新打包并重启 Web，再强刷浏览器。

## 默认路径（本机约定）

- 仓库根：`/home/tlx/projects/MaxKB`
- 一条命令打包：`bash scripts/build-ui-static.sh`（含 Node≥20 检查、`npm install`、管理端与对话端 build、`collectstatic`）
- 细节与 Node 一次性安装：见 `docs/after_sales_assistant/09_本机启动与前端构建说明.md`

## Agent 执行顺序（给用户的最短路径）

1. 在仓库根执行：`bash scripts/build-ui-static.sh`
2. 若 Web 已在跑：停掉后再起 `./.venv/bin/python main.py dev web`（另终端 Celery 照旧）
3. 提醒用户浏览器对管理端地址执行 Ctrl+Shift+R

## 不要假设

- 不要假设用户已长期开着 `ui` 里 `npm run dev`；若未说明，按「集成环境 8080」路径处理。
