# 新项目 Claude Code 并行开发任务单

## 1. 文档用途

这份文档是给后续 Claude Code 实际执行用的，不再讲抽象方向，只讲怎么拆任务、每条线做什么、建议落哪些文件、做到什么算完成。

适用前提：

- 总体路线已经确定为内部 Web 系统 + MaxKB 二开
- 一期范围已经锁定为会议纪要、日报任务、文件问答与受控改表
- 当前优先目标是做出可演示的 V1，而不是一次做完所有企业办公能力
- 最终交付物不是完整 MaxKB，而是裁剪后的办公 Agent 精简版

## 2. 开发总原则

### 2.1 主会话只做总控

主会话不要直接把所有模块代码都写掉，只做下面几件事：

1. 确认数据模型
2. 确认接口契约
3. 确认目录结构
4. 分配子会话任务
5. 做合并前验收

### 2.2 子会话只负责一个模块

每个子会话只负责一条业务线，不交叉改动其他模块的核心文件。

推荐拆法：

- 子线 A：用户、部门、通知绑定、权限扩展
- 子线 B：会议纪要
- 子线 C：日报与任务池
- 子线 D：文件问答与受控改表

### 2.3 公共边界要先锁死

在子线开始前，必须先由主会话锁死这 4 类公共信息：

1. 数据表名称和字段名
2. API 路径
3. 前端路由名称
4. 任务状态和枚举值

否则 4 个会话并行时很容易互相打架。

### 2.4 原生功能裁剪原则

这次开发不是“保留原版 MaxKB 全量功能再叠加新模块”，而是“基于 MaxKB 底座做精简版新项目”。

所以主会话必须额外负责一件事：

- 明确哪些原生功能只隐藏入口
- 明确哪些原生功能后续彻底删除

裁剪顺序固定为：

1. 先保留底层依赖
2. 先关闭前端菜单、路由、无关页面入口
3. 再关闭无关接口暴露
4. 最后做源码级删除

不要一开始就直接删掉 `users`、`knowledge`、`oss` 等底层依赖模块。

## 3. 推荐目录落点

### 3.1 后端目录

后端建议新增业务应用：

- `apps/office_agent/`

建议目录：

- `apps/office_agent/models/`
- `apps/office_agent/api/`
- `apps/office_agent/serializers/`
- `apps/office_agent/service/`
- `apps/office_agent/tasks/`
- `apps/office_agent/constants/`
- `apps/office_agent/urls.py`

### 3.2 前端目录

前端建议新增：

- `ui/src/views/office-agent/`
- `ui/src/router/modules/office-agent.ts`
- `ui/src/api/office-agent/`
- `ui/src/types/office-agent/`

推荐页面目录：

- `ui/src/views/office-agent/dashboard/`
- `ui/src/views/office-agent/meeting/`
- `ui/src/views/office-agent/report/`
- `ui/src/views/office-agent/task/`
- `ui/src/views/office-agent/file-qa/`
- `ui/src/views/office-agent/table-ops/`
- `ui/src/views/office-agent/admin/`

## 4. 主会话任务单

主会话按下面顺序执行，不要跳。

### 任务 1：建立业务应用骨架

目标：

- 建好 `office_agent` 应用目录
- 把 `urls.py` 接入总路由
- 确认前后端命名风格

建议涉及文件：

- `apps/office_agent/__init__.py`
- `apps/office_agent/apps.py`
- `apps/office_agent/urls.py`
- `apps/maxkb/urls/web.py`
- `ui/src/router/modules/office-agent.ts`

完成标准：

- 后端可识别 `office_agent` 应用
- 前端路由有占位入口
- 不影响现有模块访问

### 任务 1.5：梳理原生功能裁剪清单

目标：

- 列出哪些 MaxKB 原生功能需要保留
- 列出哪些功能只隐藏入口
- 列出哪些功能后续彻底删除

建议涉及范围：

- 前端菜单
- 前端路由
- 后端总路由暴露
- 原生管理页面

首批建议隐藏或删除的对象：

- 多模型管理相关页面
- 与你项目无关的原生应用管理页面
- 与你项目无关的通用触发器页面
- 与你项目无关的工具市场和通用工作流入口

完成标准：

- 有一份清晰裁剪清单
- 主会话知道哪些模块暂时不能动
- 子会话不会误保留无关功能

### 任务 2：锁定数据模型

目标：

- 建立用户扩展、会议、日报、任务、文件、审计相关模型

建议涉及文件：

- `apps/office_agent/models/employee.py`
- `apps/office_agent/models/meeting.py`
- `apps/office_agent/models/report.py`
- `apps/office_agent/models/task.py`
- `apps/office_agent/models/file_asset.py`
- `apps/office_agent/models/table_ops.py`
- `apps/office_agent/models/__init__.py`

完成标准：

- 核心表结构清晰
- 枚举值统一
- 迁移文件可生成

### 任务 3：锁定接口契约

目标：

- 先把会议、日报、任务、文件问答、表格操作接口名定下来

建议涉及文件：

- `apps/office_agent/api/meeting.py`
- `apps/office_agent/api/report.py`
- `apps/office_agent/api/task.py`
- `apps/office_agent/api/file_qa.py`
- `apps/office_agent/api/table_ops.py`

完成标准：

- 主要 API 路径确定
- 请求参数与响应字段有统一格式
- 子线可以按契约并行实现

### 任务 4：第一轮界面精简

目标：

- 让系统前台只暴露办公 Agent 需要的页面入口

建议涉及文件：

- `ui/src/router/modules/`
- 菜单配置相关文件
- 与办公 Agent 无关的首页入口

完成标准：

- 用户进入系统后，优先看到办公 Agent 相关入口
- 与新项目无关的原生入口被隐藏
- 不影响底层依赖模块被内部调用

## 5. 子线 A：用户、部门、通知绑定、权限扩展

### 5.1 目标

让系统具备“谁是谁、属于哪个部门、可以发到哪里”的能力。

### 5.2 范围

只做：

- 员工扩展资料
- 部门表
- 通知绑定表
- 页面上的员工管理和绑定管理

不做：

- 外部单点登录
- 企业微信自动同步组织架构
- 飞书通讯录自动同步

### 5.3 建议文件

后端：

- `apps/office_agent/models/employee.py`
- `apps/office_agent/serializers/employee.py`
- `apps/office_agent/api/employee.py`
- `apps/office_agent/service/permission_service.py`

前端：

- `ui/src/views/office-agent/admin/employee/index.vue`
- `ui/src/views/office-agent/admin/employee/EmployeeDrawer.vue`
- `ui/src/views/office-agent/admin/employee/BindingDrawer.vue`
- `ui/src/api/office-agent/employee.ts`

### 5.4 完成标准

- 管理员可以创建员工扩展资料
- 可以设置部门
- 可以填写邮箱、手机号、企业微信、飞书绑定信息
- 员工登录后能识别自己的业务身份

## 6. 子线 B：会议纪要

### 6.1 目标

把会议转写文本变成结构化纪要，并落任务项。

### 6.2 范围

只做：

- 粘贴转写文本
- 术语识别
- 待确认项
- 纪要生成
- PDF 导出
- 任务抽取

不做：

- 会议音频转写
- 腾讯会议自动抓取

### 6.3 建议文件

后端：

- `apps/office_agent/models/meeting.py`
- `apps/office_agent/service/meeting_term_service.py`
- `apps/office_agent/service/meeting_summary_service.py`
- `apps/office_agent/service/meeting_pdf_service.py`
- `apps/office_agent/api/meeting.py`

前端：

- `ui/src/views/office-agent/meeting/index.vue`
- `ui/src/views/office-agent/meeting/MeetingConfirmPanel.vue`
- `ui/src/views/office-agent/meeting/MeetingSummaryPreview.vue`
- `ui/src/api/office-agent/meeting.ts`

### 6.4 复用点

- 对话与生成逻辑优先复用 `apps/application/chat_pipeline`
- 文件回传优先复用 `apps/oss`

### 6.5 完成标准

- 一段会议文本可以生成纪要
- 术语确认可交互
- 可以导出 PDF
- 能抽出任务项并写入任务池

## 7. 子线 C：日报与任务池

### 7.1 目标

让日报变成结构化任务状态，并产出次日提醒。

### 7.2 范围

只做：

- 日报 PDF 上传
- 结构化日报补录
- 任务提取
- 任务状态更新
- 同名文件版本替换
- 今日提醒内容生成

不做：

- 多级审批流
- 绩效打分
- 复杂项目管理看板

### 7.3 建议文件

后端：

- `apps/office_agent/models/report.py`
- `apps/office_agent/models/task.py`
- `apps/office_agent/service/report_parse_service.py`
- `apps/office_agent/service/task_match_service.py`
- `apps/office_agent/service/reminder_service.py`
- `apps/office_agent/tasks/daily_digest.py`
- `apps/office_agent/api/report.py`
- `apps/office_agent/api/task.py`

前端：

- `ui/src/views/office-agent/report/index.vue`
- `ui/src/views/office-agent/task/index.vue`
- `ui/src/views/office-agent/task/TaskDetailDrawer.vue`
- `ui/src/views/office-agent/dashboard/index.vue`
- `ui/src/api/office-agent/report.ts`
- `ui/src/api/office-agent/task.ts`

### 7.4 复用点

- 提醒调度优先收敛在 `office_agent/tasks/`
- 如果早期需要借用现有调度能力，可以临时复用，但最终不保留原生触发器页面

### 7.5 完成标准

- 上传日报后能生成任务项
- 同名任务文件有版本替换机制
- 员工登录后能看到自己的任务状态和今日提醒

## 8. 子线 D：文件问答与受控改表

### 8.1 目标

让文档可问答、源文件可回看、库存表可自然语言查询和受控修改。

### 8.2 范围

只做：

- 文件上传登记
- 测试报告问答
- 命中文档源文件打开
- 1 张业务表的自然语言查询
- 1 张业务表的受控修改预览与确认

不做：

- 所有表通用引擎
- 任意文档自由写回

### 8.3 建议文件

后端：

- `apps/office_agent/models/file_asset.py`
- `apps/office_agent/models/table_ops.py`
- `apps/office_agent/service/file_asset_service.py`
- `apps/office_agent/service/file_qa_service.py`
- `apps/office_agent/service/table_query_service.py`
- `apps/office_agent/service/table_write_guard_service.py`
- `apps/office_agent/api/file_qa.py`
- `apps/office_agent/api/table_ops.py`

前端：

- `ui/src/views/office-agent/file-qa/index.vue`
- `ui/src/views/office-agent/file-qa/SourceFileDrawer.vue`
- `ui/src/views/office-agent/table-ops/index.vue`
- `ui/src/views/office-agent/table-ops/ChangePreviewDialog.vue`
- `ui/src/api/office-agent/file-qa.ts`
- `ui/src/api/office-agent/table-ops.ts`

### 8.4 复用点

- 文档问答优先复用 `apps/knowledge`
- 原文件访问优先复用 `apps/oss/retrieval_urls.py`
- SQL 安全门闸思路参考当前仓库已有实现

### 8.5 完成标准

- 用户问测试报告相关问题时能拿到回答
- 回答里能看到并打开原文件
- 自然语言修改库存表时必须先预览再确认
- 所有写操作都有审计记录

## 9. 联调顺序

不要 4 条线都写完再一次性联调，正确顺序如下：

1. 主会话先合并应用骨架、裁剪清单和模型基础
2. 先完成第一轮界面精简，隐藏无关原生入口
3. 合并子线 A，先让员工身份与权限稳定
4. 合并子线 B，打通会议纪要闭环
5. 合并子线 C，接日报和任务池
6. 合并子线 D，最后再接文件问答与表格写操作
7. 最后统一接提醒调度、源码裁剪和部署

## 10. 每条线交付时必须回报的内容

每个 Claude Code 子会话提交结果时，必须带回这 5 类信息：

1. 改了哪些文件
2. 完成了哪些业务点
3. 没完成什么
4. 跑了什么验证
5. 有哪些依赖主会话继续处理

## 11. 推荐提示词模板

### 11.1 主会话给子会话的模板

你只负责以下模块：

- 模块名称：
- 业务目标：
- 允许修改的目录：
- 不允许修改的目录：
- 上游依赖：
- 输出文件：
- 验收标准：

注意：

- 不要改其他模块的公共枚举
- 不要重命名已锁定字段
- 完成后给出验证命令和结果

### 11.2 子会话自检模板

提交前自检：

1. 有没有改到不该改的文件
2. 字段名是否和蓝图一致
3. 路由名是否和主会话约定一致
4. 有没有最小验证结果
5. 有没有留下未说明的风险点

## 12. 这一轮开发最值得先做的最小闭环

如果你想尽快出一个能给老板演示的版本，建议先只做下面这个最小闭环：

1. 员工登录
2. 粘贴会议转写文本
3. 生成纪要 PDF
4. 抽取任务项
5. 员工工作台看到任务

这个闭环最短、最容易直观看到价值，也最适合作为第一轮演示。

## 13. 这份任务单怎么用

推荐用法：

1. 主会话先按第 4 节做骨架、裁剪清单和契约
2. 先做第一轮入口精简，再从第 5 到第 8 节里挑一条子线开始
3. 每完成一条线就合并并验收，不要囤到最后
4. 第一轮优先完成最小闭环，再扩日报和文件问答
