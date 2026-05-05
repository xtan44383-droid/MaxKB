#!/usr/bin/env python3
# coding: utf-8
"""
首批 30 题一键测试：
1. 读取同目录 local_secrets.json
2. 调用现有 run_eval.py 跑 first_batch_cases.json
3. 生成 first_batch_report.json / first_batch_report.txt
4. 自动写入 docs/after_sales_assistant/13_首批问题测试.md
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SECRETS = HERE / "local_secrets.json"
CASES = HERE / "first_batch_cases.json"
REPORT = HERE / "first_batch_report.json"
DOC = ROOT / "docs" / "after_sales_assistant" / "13_首批问题测试.md"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def format_expect(expect: dict) -> str:
    parts: list[str] = []
    if expect.get("answer_contains_all"):
        parts.append("应包含: " + " / ".join(expect["answer_contains_all"]))
    if expect.get("answer_contains_any"):
        parts.append("至少包含其一: " + " / ".join(expect["answer_contains_any"]))
    if expect.get("answer_not_contains"):
        parts.append("不应包含: " + " / ".join(expect["answer_not_contains"]))
    return "；".join(parts) if parts else "未设置自动规则"


def build_case_meta_map(cases_data: dict) -> dict:
    result = {}
    for row in cases_data.get("cases", []):
        result[row["id"]] = {
            "expect_note": row.get("expect_note", ""),
            "expect_rule_text": format_expect(row.get("expect", {})),
            "category": row.get("category", "未分类"),
        }
    return result


def render_markdown_doc(secrets: dict, report: dict, cases_data: dict) -> str:
    summary = report.get("summary", {})
    analysis = report.get("summary_analysis", {})
    results = report.get("results", [])
    case_meta = build_case_meta_map(cases_data)

    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for row in results:
        category = row.get("category") or case_meta.get(row.get("id"), {}).get("category", "未分类")
        grouped.setdefault(category, []).append(row)

    lines: list[str] = []
    lines.append("# 首批问题测试")
    lines.append("")
    lines.append("本文由 `scripts/after_sales_assistant_eval/first_batch_one_click.py` 自动生成。")
    lines.append("用于记录当前已上传 5 篇文档下的首批 30 题 baseline 测试结果。")
    lines.append("")
    lines.append("## 1. 测试范围")
    lines.append("")
    lines.append("- 用例来源：`docs/after_sales_assistant/12 二开方向 gpt.md` 第 12 节")
    lines.append("- 用例文件：`scripts/after_sales_assistant_eval/first_batch_cases.json`")
    lines.append("- 文档包：`mock_data/knowledge/after_sales_upload_ready.zip`")
    lines.append("- 生成时间：`%s`" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("- MaxKB 地址：`%s`" % str(secrets.get("maxkb_base", "")).rstrip("/"))
    lines.append("- 应用 ID：`%s`" % str(secrets.get("maxkb_app_id", "")).strip())
    lines.append("")
    lines.append("## 2. 自动规则汇总")
    lines.append("")
    lines.append("- 总题数：%s" % summary.get("total", 0))
    lines.append("- 自动判定通过：%s" % summary.get("pass", 0))
    lines.append("- 自动判定未通过：%s" % summary.get("fail", 0))
    lines.append("- 自动规则通过率：%s%%" % summary.get("pass_rate_percent", 0))
    if analysis.get("简读"):
        lines.append("- 简读：%s" % analysis["简读"])
    lines.append("")
    lines.append("说明：这里的“符合预期 / 不符合预期”是按关键词规则自动判定，不等同于最终人工语义结论。")
    lines.append("")
    lines.append("## 3. 分题结果")
    lines.append("")

    for category, rows in grouped.items():
        lines.append("### %s" % category)
        lines.append("")
        for row in rows:
            meta = case_meta.get(row.get("id"), {})
            lines.append("#### %s" % row.get("id", "UNKNOWN"))
            lines.append("")
            lines.append("- 问题：%s" % row.get("question", ""))
            if meta.get("expect_note"):
                lines.append("- 预期要点：%s" % meta["expect_note"])
            lines.append("- 自动规则：%s" % meta.get("expect_rule_text", "未设置自动规则"))
            lines.append("- 自动判定：%s" % ("符合预期" if row.get("ok") else "不符合预期"))
            lines.append("- HTTP 状态：%s" % row.get("http_status"))
            lines.append("- 耗时：%ss" % row.get("latency_s"))
            if row.get("errors"):
                lines.append("- 自动判定原因：%s" % "；".join(row["errors"]))
            else:
                lines.append("- 自动判定原因：无")
            lines.append("- 回答：")
            lines.append("")
            answer = str(row.get("answer", "")).strip()
            if answer:
                lines.append(answer)
            else:
                lines.append("（无内容）")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    if not SECRETS.is_file():
        print(f"缺少 {SECRETS}，请先填写本地配置。", file=sys.stderr)
        return 2
    if not CASES.is_file():
        print(f"缺少 {CASES}，无法执行首批问题测试。", file=sys.stderr)
        return 2

    secrets = load_json(SECRETS)
    base = str(secrets.get("maxkb_base", "http://localhost:8080")).rstrip("/")
    chat_path = str(secrets.get("maxkb_chat_path", "/chat")).strip() or "/chat"
    app_id = str(secrets.get("maxkb_app_id", "")).strip()
    api_key = str(secrets.get("maxkb_api_key", "")).strip()
    if not app_id or not api_key:
        print("local_secrets.json 缺少应用 ID 或 API 密钥。", file=sys.stderr)
        return 2

    os.chdir(HERE)
    sys.path.insert(0, str(HERE))
    import argparse
    import run_eval  # noqa: E402

    args = argparse.Namespace(
        cases=str(CASES),
        base=base,
        chat_path=chat_path,
        app_id=app_id,
        api_key=api_key,
        timeout=300,
        sleep_s=0.3,
        output=str(REPORT),
    )
    exit_code = run_eval.run(args)

    report = load_json(REPORT)
    cases_data = load_json(CASES)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    with open(DOC, "w", encoding="utf-8") as f:
        f.write(render_markdown_doc(secrets, report, cases_data))

    print(f"已写 Markdown: {DOC}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
