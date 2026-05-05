#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地校验 mock_data/text2sql 安全查询逻辑；离线部分不依赖数据库，连库部分需 Postgres 已导入 after_sales_demo。"""
import importlib.util
import os
import sys

# 仓库根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_PATH = os.path.join(ROOT, "mock_data", "text2sql", "safe_pg_tool_for_maxkb.py")


def run_offline_validation(mod):
    """不连库：仅校验 SQL 白名单与单语句逻辑。"""
    v = mod._validate_readonly_select
    out = v("SELECT COUNT(*) AS c FROM tickets")
    assert "LIMIT" in out.upper(), out

    try:
        v("SELECT * FROM tickets; DELETE FROM tickets WHERE 1=1")
    except Exception:
        pass
    else:
        raise AssertionError("多语句应被拒绝")

    try:
        v("INSERT INTO tickets (ticket_id) VALUES ('x')")
    except Exception as e:
        if not ("禁止" in str(e) or "关键字" in str(e) or "仅允许" in str(e)):
            raise
    else:
        raise AssertionError("INSERT 应被拒绝")

    try:
        v("SELECT * FROM unknown_table")
    except Exception as e:
        if "不允许查询表" not in str(e):
            raise
    else:
        raise AssertionError("非白名单表应被拒绝")

    # 字面量中含 delete 字样不应误判
    v(
        "SELECT ticket_id FROM tickets WHERE issue_summary LIKE '%delete%' LIMIT 5"
    )

    print("OK: offline SQL validation")


def main():
    spec = importlib.util.spec_from_file_location("safe_pg_tool_for_maxkb", TOOL_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    run_offline_validation(mod)

    host = os.environ.get("PGHOST", "127.0.0.1")
    port = os.environ.get("PGPORT", "15432")
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "Password123@postgres")
    database = os.environ.get("PGDATABASE", "after_sales_demo")

    fn = mod.after_sales_demo_readonly_query
    kwargs = dict(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
    )

    try:
        out = fn(sql="SELECT COUNT(*) AS c FROM tickets", **kwargs)
    except Exception as e:
        if "Connection refused" in str(e) or "connection failed" in str(e).lower():
            print("SKIP: Postgres 未启动或端口不可达，已跳过连库用例")
            print("verify_text2sql_tool: 离线校验通过")
            return
        raise

    assert '"row_count": 1' in out or "12" in out, out
    print("OK: SELECT COUNT (integration)")

    try:
        fn(sql="SELECT * FROM tickets; DELETE FROM tickets WHERE 1=1", **kwargs)
    except Exception:
        pass
    else:
        print("FAIL: multi-statement should raise", file=sys.stderr)
        sys.exit(1)
    print("OK: reject multi-statement (integration)")

    try:
        fn(sql="INSERT INTO tickets (ticket_id) VALUES ('x')", **kwargs)
    except Exception as e:
        if "禁止" in str(e) or "关键字" in str(e) or "仅允许" in str(e):
            print("OK: reject INSERT (integration)")
        else:
            raise
    else:
        print("FAIL: INSERT should raise", file=sys.stderr)
        sys.exit(1)

    print("verify_text2sql_tool: 全部通过（含连库）")


if __name__ == "__main__":
    main()
