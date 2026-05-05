#!/usr/bin/env python3
# coding: utf-8
"""
对 MaxKB「工作流 / 知识 / Text2SQL」类应用做批量联调用例评估（减轻手工逐条问+记结果）。

说明：
- 调用方式与产品一致：公开放问接口 `POST {base}{chat_path}/api/{application_id}/chat/completions`
- 使用「应用 API 密钥」认证，密钥格式在后台创建后为 application- 或 agent- 开头。
- 每条用例独立发问：不在请求体里带 chat_id，让服务端按 OpenAPI 逻辑新建会话（自造 chat_id 会报 Conversation does not exist）。
- 本脚本做可自动化的规则验收（子串/黑名单）；可扩展 judge，不替代人工抽检。
- 使用 -o report.json 时，同目录自动生成 report.txt（问与答全文，UTF-8）。

环境变量（也可用命令行传参，见 --help）：
- MAXKB_BASE        如 http://127.0.0.1:8080
- MAXKB_CHAT_PATH   默认 /chat（与 config 中 CHAT_PATH 一致，多数安装为 /chat）
- MAXKB_APP_ID      工作流应用 UUID
- MAXKB_API_KEY     应用 API 密钥
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("需要安装 requests: pip install requests", file=sys.stderr)
    raise SystemExit(1)


@dataclass
class Case:
    id: str
    question: str
    expect: dict
    category: str = ""


@dataclass
class CaseResult:
    case_id: str
    question: str
    ok: bool
    answer: str
    answer_preview: str
    errors: List[str] = field(default_factory=list)
    latency_s: float = 0.0
    http_status: Optional[int] = None
    category: str = ""


def summarize_results(results: List[CaseResult]) -> Dict[str, Any]:
    """
    在「规则可自动检查」范围内做汇总，不等同于人工语义上的绝对对错。
    """
    total = len(results)
    pass_n = sum(1 for r in results if r.ok)
    fail_n = total - pass_n
    rate = round(100.0 * pass_n / total, 1) if total else 0.0
    by_cat: Dict[str, Dict[str, int]] = defaultdict(lambda: {"pass": 0, "fail": 0})
    for r in results:
        key = (r.category or "未分类").strip() or "未分类"
        if r.ok:
            by_cat[key]["pass"] += 1
        else:
            by_cat[key]["fail"] += 1
    err_kind: Counter = Counter()
    fail_ids: Dict[str, List[str]] = defaultdict(list)
    for r in results:
        if r.ok:
            continue
        fail_ids[r.category or "未分类"].append(r.case_id)
        for e in r.errors:
            if "请求失败" in e or (isinstance(e, str) and e.strip().startswith("HTTP")):
                err_kind["请求或HTTP异常"] += 1
            elif "回答为空" in e:
                err_kind["最终回答为空(接口无内容)"] += 1
            elif "应至少包含其一" in e:
                err_kind["未命中子串(任选之一)"] += 1
            elif "应包含" in e:
                err_kind["未命中子串(全部必含)"] += 1
            elif "不应出现" in e:
                err_kind["触发了不应出现的子串(黑名单)"] += 1
            else:
                err_kind["其它原因"] += 1
    ranked = sorted(
        ((k, v["fail"], v["pass"]) for k, v in by_cat.items() if v["fail"] > 0),
        key=lambda x: -x[1],
    )
    top_cat_note = ""
    if ranked:
        c0, f0, _p0 = ranked[0]
        top_cat_note = "失败用例在分类上多集中在: %s（%d 条未过）" % (c0, f0)
    top_errs = err_kind.most_common(3)
    err_note = "；".join(
        ["%s: %d 次" % (a, b) for a, b in top_errs]
    ) if top_errs else "无"
    return {
        "统计说明": "在 eval_cases 里写的子串/黑名单规则下，自动判定通过条数。漏检语义错误、或规则写得太松仍 PASS，都需人审。",
        "总条数": total,
        "规则判定通过": pass_n,
        "未通过": fail_n,
        "规则通过率_百分比": rate,
        "按分类_通过_失败": {k: {"通过": v["pass"], "未通过": v["fail"]} for k, v in by_cat.items()},
        "未通过数较多的分类_降序": [
            {"分类": a[0], "未通过": a[1], "通过": a[2]} for a in ranked
        ],
        "未通过用例ID_按分类": {k: v for k, v in fail_ids.items() if v},
        "未通过条目中错误类型出现次数": dict(err_kind.most_common()),
        "简读": top_cat_note + ("。未通过时常见自动判定原因: " + err_note if err_note else ""),
    }


def _append_summary_to_text(lines: List[str], s: Dict[str, Any]) -> None:
    lines.append("【汇总】（规则可检范围，非纯粹语义「准确率」）")
    lines.append("总条数: %d  规则通过: %d  未通过: %d  通过率(规则): %s%%" % (
        s.get("总条数", 0), s.get("规则判定通过", 0), s.get("未通过", 0), s.get("规则通过率_百分比", 0)
    ))
    lines.append("说明: %s" % s.get("统计说明", ""))
    if s.get("简读"):
        lines.append("简读: %s" % s["简读"])
    lines.append("")
    lines.append("未通过: 各分类条数(仅列出有未通过的类)")
    for row in s.get("未通过数较多的分类_降序", []):
        lines.append("  - %s: 未通过 %d, 通过 %d" % (row.get("分类"), row.get("未通过", 0), row.get("通过", 0)))
    lines.append("")
    lines.append("未通过: 自动判定里错误原因出现次数（同一条可多项）")
    for a, b in (s.get("未通过条目中错误类型出现次数") or {}).items():
        lines.append("  - %s: %d" % (a, b))
    if s.get("未通过用例ID_按分类"):
        lines.append("")
        lines.append("未通过用例 ID（按分类）")
        for cat, ids in s["未通过用例ID_按分类"].items():
            lines.append("  - %s: %s" % (cat, ", ".join(ids)))
    lines.append("")
    lines.append("=" * 60)
    lines.append("")


def _append_failed_tail(
    lines: List[str],
    results: List[CaseResult],
    summary: Dict[str, Any],
) -> None:
    """
    在 report.txt 文末追加「未通过速览」，便于直接拖到最后一眼看到是哪些问题没过。
    """
    failed = [r for r in results if not r.ok]
    lines.append("=" * 60)
    lines.append("")
    lines.append("【未通过速览】（文末一眼查看；完整回答与上下文见上文同 ID 条目）")
    if not failed:
        lines.append("本次全部通过，无失败条。")
        lines.append("")
        return
    lines.append("未通过条数: %d / 总 %d" % (len(failed), len(results)))
    err_dist = summary.get("未通过条目中错误类型出现次数") or {}
    if err_dist:
        parts = ["%s×%d" % (k, v) for k, v in sorted(err_dist.items(), key=lambda x: -x[1])]
        lines.append("自动判定原因分布（同一条可多项）: " + "；".join(parts))
    # 根据本次失败类型写一句归纳，便于对照画布/接口
    kinds = set()
    for r in failed:
        for e in r.errors:
            if "回答为空" in e or "HTTP" in e or "请求失败" in e:
                kinds.add("empty_or_http")
            elif "应至少包含其一" in e:
                kinds.add("any_miss")
            elif "应包含" in e and "不应出现" not in e:
                kinds.add("all_miss")
            elif "不应出现" in e:
                kinds.add("blacklist")
    note_parts: List[str] = []
    if "empty_or_http" in kinds:
        note_parts.append("回答为空或请求异常时，多为接口未带回最终 content、工作流未走到输出节点或超时")
    if "all_miss" in kinds or "any_miss" in kinds:
        note_parts.append("子串未命中多为模型措辞与 eval_cases 里规则不一致，可调预期子串或收紧画布提示词")
    if "blacklist" in kinds:
        note_parts.append("黑名单命中表示回答里出现了不应出现的措辞")
    if note_parts:
        lines.append("归纳: " + "；".join(note_parts))
    lines.append("")
    for i, r in enumerate(failed, 1):
        q_one = (r.question or "").strip().replace("\n", " ")
        lines.append("%d) [%s] %s" % (i, r.case_id, (r.category or "未分类").strip() or "未分类"))
        lines.append("   问: %s" % q_one)
        if r.errors:
            for e in r.errors:
                lines.append("   判: %s" % e)
        else:
            lines.append("   判: （无具体规则项，见上文）")
        lines.append("")
    lines.append("=" * 60)
    lines.append("")


def write_text_report(
    path: str,
    base: str,
    app_id: str,
    results: List[CaseResult],
    summary: Optional[Dict[str, Any]] = None,
) -> None:
    """生成可读文本文档，含汇总与每题详情。"""
    s = summary if summary is not None else summarize_results(results)
    lines: List[str] = []
    lines.append("售后工作流/应用 联调结果（本机生成）")
    lines.append("时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("基址: " + base)
    lines.append("应用 ID: " + app_id)
    _append_summary_to_text(lines, s)
    for r in results:
        lines.append("")
        lines.append("[%s] %s" % (r.case_id, r.category or "未分类"))
        lines.append("结果: %s" % ("PASS" if r.ok else "FAIL"))
        lines.append("HTTP: %s  耗时: %.2fs" % (r.http_status, r.latency_s))
        lines.append("问题:")
        lines.append(r.question)
        lines.append("回答:")
        if r.answer:
            lines.append(r.answer)
        else:
            lines.append("（无内容）")
        if r.errors:
            lines.append("未通过/异常原因:")
            for e in r.errors:
                lines.append("  - " + e)
        lines.append("-" * 60)
    _append_failed_tail(lines, results, s)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def load_cases(path: str) -> List[Case]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for row in data.get("cases", []):
        out.append(
            Case(
                id=row.get("id", "?"),
                question=row["question"],
                expect=row.get("expect", {}),
                category=row.get("category", ""),
            )
        )
    return out


def normalize(s: str, case_insensitive: bool) -> str:
    return s.lower() if case_insensitive else s


def check_expect(answer: str, expect: dict) -> List[str]:
    """对最终可见回答做子串/黑名单检查；不解析工作流 details（需管理员接口另做）。"""
    err: List[str] = []
    if not (answer and str(answer).strip()):
        return ["回答为空"]
    ins = expect.get("case_insensitive", True)
    ans = normalize(answer, ins)
    for sub in expect.get("answer_contains_all", []) or []:
        subn = normalize(sub, ins)
        if subn not in ans:
            err.append(f"应包含: {sub!r}")
    any_list = expect.get("answer_contains_any", [])
    if any_list and not any(normalize(x, ins) in ans for x in any_list):
        err.append(f"应至少包含其一: {any_list!r}")
    for sub in expect.get("answer_not_contains", []) or []:
        subn = normalize(sub, ins)
        if subn in ans:
            err.append(f"不应出现: {sub!r}")
    return err


def chat_completions(
    base: str,
    chat_path: str,
    app_id: str,
    api_key: str,
    user_message: str,
    stream: bool,
    timeout: int,
) -> Tuple[Optional[dict], int, Optional[str]]:
    """
    返回 (json_body, http_status, error_str)
    """
    base = base.rstrip("/")
    path = chat_path.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    url = f"{base}{path}/api/{app_id}/chat/completions"
    # 与 ChatTokenAuth: Bearer application-xxx
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # 新会话，固定 chat_user_id 便于对端统计；每条问题可换新 id 避免串话
    # 不要带 chat_id：否则服务端会当作「续接已有会话」，随机 UUID 在缓存中不存在会 500。
    payload = {
        "messages": [{"role": "user", "content": user_message}],
        "stream": stream,
        "re_chat": False,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as e:
        return None, 0, str(e)
    try:
        body = r.json()
    except Exception:
        body = None
    return body, r.status_code, None


def extract_answer_block(body: dict) -> str:
    """从 OpenAI 块式响应里取主回复（与 OpenaiToResponse 一致）。"""
    if not body:
        return ""
    ch = body.get("choices") or []
    if not ch:
        return ""
    msg = ch[0].get("message") or {}
    c = msg.get("content", "")
    return c if c is not None else ""


def run(args: argparse.Namespace) -> int:
    base = args.base or os.environ.get("MAXKB_BASE", "http://127.0.0.1:8080")
    chat_path = args.chat_path or os.environ.get("MAXKB_CHAT_PATH", "/chat")
    app_id = args.app_id or os.environ.get("MAXKB_APP_ID", "")
    api_key = args.api_key or os.environ.get("MAXKB_API_KEY", "")
    if not app_id or not api_key:
        print("请设置 --app-id / --api-key 或环境变量 MAXKB_APP_ID、MAXKB_API_KEY", file=sys.stderr)
        return 2
    cases = load_cases(args.cases)
    if not cases:
        print("用例文件为空", file=sys.stderr)
        return 2
    print(f"共 {len(cases)} 条，基址: {base}，CHAT_PATH: {chat_path}，app_id: {app_id}\n")
    results: List[CaseResult] = []
    for c in cases:
        t0 = time.time()
        body, status, err = chat_completions(
            base, chat_path, app_id, api_key, c.question, stream=False, timeout=args.timeout
        )
        latency = time.time() - t0
        if err:
            results.append(
                CaseResult(
                    c.id,
                    c.question,
                    False,
                    "",
                    "",
                    [f"请求失败: {err}"],
                    latency,
                    status,
                    c.category,
                )
            )
            continue
        if status != 200 or not body:
            results.append(
                CaseResult(
                    c.id,
                    c.question,
                    False,
                    "",
                    "",
                    [f"HTTP {status} body={str(body)[:200]}"],
                    latency,
                    status,
                    c.category,
                )
            )
            continue
        answer = extract_answer_block(body)
        errs = check_expect(answer, c.expect)
        ok = len(errs) == 0
        prev = (answer or "").replace("\n", " ")[: 240]
        results.append(
            CaseResult(
                c.id, c.question, ok, answer or "", prev, errs, latency, status, c.category
            )
        )
        time.sleep(args.sleep_s)

    ok_n = sum(1 for r in results if r.ok)
    for r in results:
        st = "PASS" if r.ok else "FAIL"
        cat = f" [{r.category}]" if r.category else ""
        print(f"{st}  {r.case_id}{cat}  {r.latency_s:.1f}s")
        if r.answer:
            disp = (r.answer[:240] + "...") if len(r.answer) > 240 else r.answer
            print(f"  答: {disp}")
        for e in r.errors:
            print(f"  原因: {e}")
    print("-" * 40)
    print(
        "合计(规则): {}/{} 通过，未通过 {} 条".format(ok_n, len(results), len(results) - ok_n)
    )
    summary = summarize_results(results)
    jian = summary.get("简读") or ""
    if jian:
        print("汇总: " + jian)
    ex = summary.get("未通过条目中错误类型出现次数") or {}
    if ex:
        top = "；".join(["{}×{}".format(k, v) for k, v in list(ex.items())[:4]])
        print("未通过中错误类型分布(摘要): " + top)
    out_path = args.output
    if out_path:
        report: Dict[str, Any] = {
            "summary": {
                "total": len(results),
                "pass": ok_n,
                "fail": len(results) - ok_n,
                "pass_rate_percent": summary.get("规则通过率_百分比"),
            },
            "summary_analysis": summary,
            "results": [
                {
                    "id": r.case_id,
                    "question": r.question,
                    "ok": r.ok,
                    "category": r.category,
                    "latency_s": round(r.latency_s, 2),
                    "http_status": r.http_status,
                    "errors": r.errors,
                    "answer": r.answer,
                    "answer_preview": r.answer_preview,
                }
                for r in results
            ],
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"已写 JSON: {out_path}")
        txt_path = str(Path(out_path).with_suffix(".txt"))
        write_text_report(txt_path, base, app_id, results, summary=summary)
        print(f"已写文本文档: {txt_path}")
    return 0 if ok_n == len(results) else 1


def main():
    p = argparse.ArgumentParser(description="售后助手/工作流应用 批量用例联调")
    p.add_argument(
        "cases",
        nargs="?",
        default=os.path.join(os.path.dirname(__file__), "eval_cases.json"),
        help="用例 JSON（默认同目录 eval_cases.json，可复制 eval_cases.example.json）",
    )
    p.add_argument("--base", default=None, help="或环境变量 MAXKB_BASE")
    p.add_argument("--chat-path", default=None, help="或 MAXKB_CHAT_PATH，默认 /chat")
    p.add_argument("--app-id", default=None, help="或 MAXKB_APP_ID")
    p.add_argument("--api-key", default=None, help="或 MAXKB_API_KEY，application- 前缀")
    p.add_argument("--timeout", type=int, default=300, help="单条请求超时秒数（工作流可能较长）")
    p.add_argument("--sleep-s", type=float, default=0.3, help="用例之间间隔，减轻限流")
    p.add_argument("-o", "--output", help="将结果写入 JSON 报告")
    args = p.parse_args()
    if not os.path.isfile(args.cases):
        print(
            f"未找到 {args.cases}，请复制 eval_cases.example.json 为 eval_cases.json 并填写。",
            file=sys.stderr,
        )
        return 2
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
