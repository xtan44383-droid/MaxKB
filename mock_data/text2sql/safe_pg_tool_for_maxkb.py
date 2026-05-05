# -*- coding: utf-8 -*-
# 本文件设计为：在 MaxKB「自定义工具」中整段粘贴（与内置 PostgreSQL 工具同属 ToolExecutor 子进程执行）。
# 要求运行环境已安装 psycopg（MaxKB 主项目 pyproject 已包含 psycopg[binary]）。
# 最后一个 def 会被 MaxKB 调用：入参 sql 来自工具输入，其余来自初始化参数。
#
# 说明：平台在 ToolExecutor 中已对 database=after_sales_demo 的 sql 做过与下方一致的只读校验（见 apps/common/utils/demo_sql_gate.py）。
# 此处保留校验，便于子进程内二次兜底；若调整白名单或关键字策略，请与 demo_sql_gate 同步。

import json
import re
from decimal import Decimal
from datetime import date, datetime


# 仅允许查询的表（与 mock_data/sql/schema.sql 一致）
_ALLOWED_TABLES = frozenset({"products", "tickets", "ticket_logs"})

# 禁止出现在语句中的危险关键字（整词匹配，降低误伤列名概率）
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|EXECUTE)\b",
    re.IGNORECASE,
)

_DEFAULT_LIMIT = 200
# 会话级超时（毫秒），防止长查询占满连接
_STATEMENT_TIMEOUT_MS = 8000


def _mask_quoted_strings(sql: str) -> str:
    """遮蔽字符串与双引号标识符，避免字面量中的词触发危险关键字检测。"""

    def _blank(m):
        return " " * len(m.group(0))

    s = re.sub(r"'(?:''|[^'])*'", _blank, sql)
    s = re.sub(r'"(?:""|[^"])*"', _blank, s)
    return s


def _strip_sql_comments(raw: str) -> str:
    """移除块注释与行注释，便于做前缀与分号检测。"""
    s = re.sub(r"/\*.*?\*/", " ", raw, flags=re.DOTALL)
    lines = []
    for line in s.splitlines():
        if "--" in line:
            line = line[: line.index("--")]
        lines.append(line)
    return "\n".join(lines)


def _split_statements(sql: str):
    """按分号拆分；忽略末尾单独分号。"""
    parts = [p.strip() for p in sql.split(";")]
    return [p for p in parts if p]


def _extract_from_join_tables(sql: str):
    """从 FROM / JOIN 后提取简单表名（第一版保守，不支持 schema.table）。"""
    found = []
    for m in re.finditer(r"(?:FROM|JOIN)\s+(\w+)", sql, re.IGNORECASE):
        name = m.group(1)
        if name.upper() not in ("SELECT", "WHERE", "ON", "AND", "OR", "NOT", "NULL"):
            found.append(name.lower())
    return found


def _validate_readonly_select(sql: str) -> str:
    """
    校验通过后返回「可执行的单条 SQL」字符串（必要时自动补 LIMIT）。
    不通过则 raise Exception（中文信息便于客服侧排查）。
    """
    cleaned = _strip_sql_comments(sql).strip()
    if not cleaned:
        raise Exception("SQL 不能为空")

    parts = _split_statements(cleaned)
    if len(parts) != 1:
        raise Exception("仅允许单条 SQL，禁止多语句（分号分隔）")

    single = parts[0]
    head = single.lstrip()
    upper_head = head[:20].upper()
    if not (upper_head.startswith("SELECT") or upper_head.startswith("WITH")):
        raise Exception("仅允许 SELECT 或以 WITH 开头的只读查询")

    if _FORBIDDEN_KEYWORDS.search(_mask_quoted_strings(single)):
        raise Exception("检测到禁止的关键字（如 INSERT/UPDATE/DELETE 等）")

    if re.search(r"\b(INFORMATION_SCHEMA|PG_CATALOG)\b", single, re.IGNORECASE):
        raise Exception("禁止查询系统目录表")

    # 禁止 schema 限定（避免绕过表白名单）
    if re.search(r"\b\w+\.(products|tickets|ticket_logs)\b", single, re.IGNORECASE):
        raise Exception("暂不支持 schema.table 写法，请直接使用表名")

    tables = _extract_from_join_tables(single)
    for t in tables:
        if t not in _ALLOWED_TABLES:
            raise Exception(f"不允许查询表: {t}，白名单为: {', '.join(sorted(_ALLOWED_TABLES))}")

    if not re.search(r"\bLIMIT\b", single, re.IGNORECASE):
        single = f"{single.rstrip().rstrip(';')} LIMIT {_DEFAULT_LIMIT}"

    return single


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    raise TypeError(f"不可序列化类型: {type(obj)}")


def after_sales_demo_readonly_query(host, port, user, password, database, sql):
    """
    售后演示库只读查询（MaxKB 自定义工具入口函数）。
    初始化参数：host, port, user, password, database
    输入参数：sql
    """
    import psycopg
    from psycopg.rows import dict_row

    safe_sql = _validate_readonly_select(sql)
    port_int = int(port) if not isinstance(port, int) else port

    conninfo = psycopg.conninfo.make_conninfo(
        host=host,
        port=port_int,
        dbname=database,
        user=user,
        password=password,
        options=f"-c statement_timeout={_STATEMENT_TIMEOUT_MS}",
    )

    rows_out = []
    with psycopg.connect(conninfo, autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(safe_sql)
            if cur.description is None:
                return json.dumps(
                    {"ok": True, "executed_sql": safe_sql, "rows": [], "row_count": 0, "columns": []},
                    ensure_ascii=False,
                    default=_json_default,
                )
            cols = [d.name for d in cur.description]
            fetched = cur.fetchall()
            rows_out = [dict(r) for r in fetched]

    return json.dumps(
        {
            "ok": True,
            "executed_sql": safe_sql,
            "columns": list(rows_out[0].keys()) if rows_out else cols,
            "row_count": len(rows_out),
            "rows": rows_out,
        },
        ensure_ascii=False,
        default=_json_default,
    )
