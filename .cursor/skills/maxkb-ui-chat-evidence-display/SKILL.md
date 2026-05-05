---
name: maxkb-ui-chat-evidence-display
description: >-
  MaxKB chat answer UI, citations, paragraph_list, and evidence popover behavior.
  Use when the user changes conversation bubbles, 回答依据, 溯源, footnotes, sup data-title,
  show_source, or files under ui/src/components/ai-chat.
---

# 对话区展示与溯源

## 常见改动入口（以本仓历史二开为准，若重构请以实际路径为准）

- 回答正文与卡片区域：`ui/src/components/ai-chat/component/answer-content/` 下相关 `index.vue` 等。
- 依据与脚标逻辑抽取：`ui/src/utils/answerEvidence.ts`（若存在则优先扩展，避免在多个组件复制同一规则）。

## 与后端字段

- 公开对话若关闭「展示来源」，后端仍可能返回 `paragraph_list` 供脚标使用；以前端 `application.show_source` 控制大块「知识来源」展示为准，具体以后端序列化与当前产品行为为准。
- 改展示层时同步确认：`apps/application/serializers/` 等与对话记录相关的字段是否仍满足前端假设。

## 验收

- 静态集成路径：改完后走 `maxkb-ui-build-static` 技能中的构建与强刷流程。
