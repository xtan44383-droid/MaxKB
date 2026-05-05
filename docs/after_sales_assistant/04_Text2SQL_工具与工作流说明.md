# Text2SQL：工具与工作流配置说明

本文说明如何在 MaxKB 中接入「售后演示库」只读查询，并与工作流中的 AI 节点配合完成 Text2SQL 第一版。

## 1. 自定义工具（CUSTOM）

### 1.1 代码来源

将 [mock_data/text2sql/safe_pg_tool_for_maxkb.py](../../mock_data/text2sql/safe_pg_tool_for_maxkb.py) **全文**粘贴到 MaxKB 工具代码框。

- 工具执行环境与官方「自定义工具」一致（子进程 + `ToolExecutor`）。
- 文件末尾函数 **`after_sales_demo_readonly_query`** 必须作为文件中**最后一个** `def`（MaxKB 会调用最后一个函数）。

### 1.2 入参与初始化参数

| 类型 | 字段 | 说明 |
|------|------|------|
| 输入 | `sql` | 一条只读查询语句 |
| 初始化 | `host` | 例：`127.0.0.1` |
| 初始化 | `port` | 例：`15432` |
| 初始化 | `user` | 例：`postgres` |
| 初始化 | `password` | 数据库密码 |
| 初始化 | `database` | 演示库名：`after_sales_demo` |

### 1.3 安全策略（第一版）

- 仅允许以 `SELECT` 或 `WITH` 开头的单条语句；禁止多语句（分号分隔多段）。
- 表名白名单：`products`、`tickets`、`ticket_logs`。
- 禁止 `schema.table` 写法；禁止 `information_schema` / `pg_catalog`。
- 若无 `LIMIT`，自动追加 `LIMIT 200`。
- 会话 `statement_timeout` 约 8 秒。

### 1.4 返回值

返回 **JSON 字符串**，主要字段：

- `ok`：是否执行成功
- `executed_sql`：实际执行的 SQL（含自动补的 LIMIT）
- `columns`、`rows`、`row_count`

下游可再接一个 AI 节点，把该 JSON 转写为中文业务摘要。

### 1.5 已知限制

- 使用 **`WITH`（公用表表达式）** 时，若 `FROM` 后出现 CTE 别名，可能被误判为「表名不在白名单」。第一版建议模型**尽量写简单 `SELECT ... FROM 白名单表`**；复杂 WITH 可在后续版本增强解析。

## 2. 工作流建议

**与「单边意图分流」的关系**：若应用需要**同一入口**下「查知识」与「查数据」二选一，请先在开始节点后接 **意图识别**（或判断器），**数据支路**再接本节链路；整体产品逻辑见 [06_单边意图分流_工作流配置.md](./06_单边意图分流_工作流配置.md)。

**仅数据支路**（意图已判定走「查数」之后）建议如下：

```mermaid
flowchart LR
  start[数据支路起点]
  ai[AI生成SQL]
  tool[工具_安全查询]
  sum[可选_AI摘要]
  start --> ai --> tool --> sum
```

1. **AI 节点**：系统提示词中粘贴下方「表结构摘要」，并明确要求：**只输出一条 SQL，不要 Markdown 代码块以外的解释**（或约定只输出 ```sql 块，再由后续节点截取——第一版建议「纯 SQL 一行」最简单）。
2. **工具库节点**：绑定上述自定义工具，将 AI 输出映射到参数 `sql`。
3. **（可选）AI 节点**：输入为工具返回的 JSON，输出自然语言结论。

## 3. AI 节点用表结构摘要（可直接粘贴）

以下内容来自演示库设计，与 [mock_data/sql/schema.sql](../../mock_data/sql/schema.sql) 一致。

```
你是售后工单数据分析助手，只能生成 PostgreSQL 只读查询。

【允许使用的表】
- products(product_model, product_name, category, warranty_months, release_year)
- tickets(ticket_id, product_model, fault_code, fault_type, region, customer_type,
  priority, status, channel, handler_name, created_at, closed_at,
  satisfaction_score, is_escalated, issue_summary)
- ticket_logs(log_id, ticket_id, action_type, action_note, operator_name, action_time)

【规则】
- 只输出一条 SQL；必须以 SELECT 开头；不要分号连接多条。
- 不要查询 information_schema 等系统表。
- 尽量带 LIMIT；若用户要全量，仍建议 LIMIT 200 以内。
- 第一版避免使用 WITH，优先简单 FROM/JOIN 白名单表。

【输出格式】
只输出 SQL 文本本身，不要其它说明。
```

## 4. 回归测试

见 [05_Text2SQL回归问题.md](./05_Text2SQL回归问题.md)。

## 5. 本地脚本校验

```bash
cd /path/to/MaxKB
PGHOST=127.0.0.1 PGPORT=15432 PGUSER=postgres PGPASSWORD='...' PGDATABASE=after_sales_demo \
  ./.venv/bin/python scripts/verify_text2sql_tool.py
```

未启动数据库时会连接失败，可先启动 Docker 中的 Postgres 并导入 `mock_data/sql/*.sql`。
