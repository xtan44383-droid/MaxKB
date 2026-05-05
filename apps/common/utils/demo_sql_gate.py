# coding=utf-8
"""
售后演示库 Text2SQL 入参门闸（平台侧，在 ToolExecutor 子进程之前执行）。

与 mock_data/text2sql/safe_pg_tool_for_maxkb.py 内校验规则保持一致；若改白名单或关键字策略请两处同步。
"""
import re
from typing import Any, Dict

from common.utils.logger import maxkb_logger

# 与 mock_data/sql/schema.sql、safe_pg_tool_for_maxkb 一致
_DEMO_DATABASE_NAME = "after_sales_demo"
_ALLOWED_TABLES = frozenset({"products", "tickets", "ticket_logs"})
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|EXECUTE)\b",
    re.IGNORECASE,
)
_DEFAULT_LIMIT = 200


def _mask_quoted_strings(sql: str) -> str:
    def _blank(m):
        return " " * len(m.group(0))

    s = re.sub(r"'(?:''|[^'])*'", _blank, sql)
    s = re.sub(r'"(?:""|[^"])*"', _blank, s)
    return s


def _strip_sql_comments(raw: str) -> str:
    s = re.sub(r"/\*.*?\*/", " ", raw, flags=re.DOTALL)
    lines = []
    for line in s.splitlines():
        if "--" in line:
            line = line[: line.index("--")]
        lines.append(line)
    return "\n".join(lines)


def _split_statements(sql: str):
    parts = [p.strip() for p in sql.split(";")]
    return [p for p in parts if p]


def _extract_from_join_tables(sql: str):
    found = []
    for m in re.finditer(r"(?:FROM|JOIN)\s+(\w+)", sql, re.IGNORECASE):
        name = m.group(1)
        if name.upper() not in ("SELECT", "WHERE", "ON", "AND", "OR", "NOT", "NULL"):
            found.append(name.lower())
    return found


def normalize_sql_input(raw: str) -> str:
    """去掉 Markdown 代码围栏等，得到待校验的 SQL 文本。"""
    if not raw or not isinstance(raw, str):
        return raw
    s = raw.strip()
    m = re.search(r"```(?:sql)?\s*([\s\S]*?)```", s, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return s


def validate_demo_readonly_sql(sql: str) -> str:
    """
    演示库只读校验，通过则返回可执行 SQL（必要时补 LIMIT）。
    不通过抛出 Exception，文案为中文。
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

    if re.search(r"\b\w+\.(products|tickets|ticket_logs)\b", single, re.IGNORECASE):
        raise Exception("暂不支持 schema.table 写法，请直接使用表名")

    tables = _extract_from_join_tables(single)
    for t in tables:
        if t not in _ALLOWED_TABLES:
            raise Exception(f"不允许查询表: {t}，白名单为: {', '.join(sorted(_ALLOWED_TABLES))}")

    if not re.search(r"\bLIMIT\b", single, re.IGNORECASE):
        single = f"{single.rstrip().rstrip(';')} LIMIT {_DEFAULT_LIMIT}"

    return single


def apply_tool_sql_gate(keywords: Dict[str, Any]) -> Dict[str, Any]:
    """
    在自定义工具进入子进程执行前调用：统一处理 sql 入参。

    - 凡带 sql 字符串：先做 Markdown 代码块剥离。
    - 仅当初始化参数 database 为 after_sales_demo 时，再做与演示库一致的只读白名单校验。
    """
    if not keywords:
        return keywords
    out = dict(keywords)
    sql_val = out.get("sql")
    if not isinstance(sql_val, str) or not sql_val.strip():
        return out

    normalized = normalize_sql_input(sql_val)
    out["sql"] = normalized

    db = out.get("database")
    if db == _DEMO_DATABASE_NAME:
        safe = validate_demo_readonly_sql(normalized)
        out["sql"] = safe
        maxkb_logger.info(
            "[演示库SQL门闸] 已对 sql 入参完成格式清理与只读校验，database=%s。",
            db,
        )
    else:
        maxkb_logger.info(
            "[SQL入参门闸] database=%s 非演示库，仅剥离 Markdown 代码块，不做表白名单校验。",
            db,
        )
    return out
