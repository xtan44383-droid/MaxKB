# Text2SQL 演示资源

## 文件说明

| 文件 | 说明 |
|------|------|
| [safe_pg_tool_for_maxkb.py](safe_pg_tool_for_maxkb.py) | 供 MaxKB **自定义工具（CUSTOM）** 整段粘贴的 Python：只读校验 + `psycopg` 执行演示库。 |
| 平台门闸 | 主仓 `apps/common/utils/demo_sql_gate.py`：凡自定义工具执行前，若入参含 `sql`，会先剥离 Markdown 代码块；`database=after_sales_demo` 时再走与本文工具一致的只读白名单校验（见 `ToolExecutor.exec_code`）。 |
| [../sql/schema.sql](../sql/schema.sql) | 表结构定义 |
| [../sql/seed.sql](../sql/seed.sql) | 演示数据 |

## MaxKB 中创建工具的步骤（摘要）

1. 工作空间 → 工具 → 新建自定义工具。
2. **入参**：`sql`，类型 string，必填。
3. **初始化参数**：`host`、`port`、`user`、`password`、`database`（演示库见项目交接说明：`after_sales_demo`）。
4. 将 `safe_pg_tool_for_maxkb.py` 的**文件全文**复制到工具代码编辑器（保留文件末尾对外暴露的函数名，与 MaxKB 要求一致：文件中**最后一个** `def` 会被调用）。
5. 工作流：若采用「多数问题只走一边」，请先在画布上做好 **意图识别 → 知识支路 / 数据支路**，仅在数据支路中接：AI 节点（只输出一条 `SELECT`）→ 工具节点映射 `sql`。说明见 [docs/after_sales_assistant/06_单边意图分流_工作流配置.md](../../docs/after_sales_assistant/06_单边意图分流_工作流配置.md)。

更完整的提示词模板见 [docs/after_sales_assistant/04_Text2SQL_工具与工作流说明.md](../../docs/after_sales_assistant/04_Text2SQL_工具与工作流说明.md)。

## 本地验证（可选）

需本机已启动 Postgres 且已导入演示库：

```bash
cd /home/tlx/projects/MaxKB
./.venv/bin/python scripts/verify_text2sql_tool.py
```
