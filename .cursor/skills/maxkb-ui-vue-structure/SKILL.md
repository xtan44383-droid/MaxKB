---
name: maxkb-ui-vue-structure
description: >-
  MaxKB Vue 3 frontend layout under ui/ (admin app vs chat app, shared packages).
  Use when adding or refactoring Vue components, routes, or when the user mentions
  ui/src, Vite, Element Plus, or MaxKB 管理端/对话端.
---

# MaxKB 前端目录与约定

## 目录

- 根：`ui/`，单一 `package.json`，脚本区分管理端与对话端构建（如 `build-only`、`build-only-chat`，以 `ui/package.json` 为准）。
- 业务 Vue 主要在：`ui/src/`（具体子目录随功能模块分布，改前先 `grep` 或glob 现有同类页面再对齐）。

## 编码约定（与本仓一致）

- 新注释与用户可见中文文案：UTF-8，避免乱码；风格与相邻文件一致。
- 不为了「整洁」顺带大改无关模块；需求范围内的改动优先复用现有组件与工具函数。

## 与后端的衔接

- 管理端接口与权限以现有 `api` 封装为准；新增字段需前后端与序列化一致。
- 知识库相关展示开关等若涉及配置，与后端 `meta` 字段命名保持一致（如售后相关已有 `meta.after_sales_mode` 等，以代码为准）。
