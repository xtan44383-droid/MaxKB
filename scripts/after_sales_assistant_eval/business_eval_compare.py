#!/usr/bin/env python3
# coding: utf-8
import argparse
import json
from collections import defaultdict


HIGH_RISK_WORDS = ["保修", "拒保", "换新", "免费维修", "费用", "时效", "质量问题", "人为损坏"]
RISKY_COMMITMENTS = ["一定保修", "一定换新", "免费维修", "必然免费", "保证当天修好", "一定是质量问题"]
REFUSE_PREFIX = "当前知识库未提供足够依据"


def load_cases(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    case_map = {}
    for c in data.get("cases", []):
        case_map[c.get("id")] = c
    return case_map


def safe_rate(numerator, denominator):
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def summarize(report, case_map):
    results = report.get("results", [])
    total = len(results)
    keyword_pass = sum(1 for r in results if r.get("ok"))
    avg_latency = round(sum((r.get("latency_s") or 0.0) for r in results) / total, 4) if total else 0.0

    refusal_total = 0
    refusal_ok = 0
    high_risk_total = 0
    high_risk_ok = 0
    useful_total = 0
    useful_ok = 0
    fail_distribution = defaultdict(int)

    for r in results:
        cid = r.get("id")
        answer = (r.get("answer") or "").strip()
        category = (r.get("category") or "未分类").strip() or "未分类"
        case = case_map.get(cid, {})
        expect = case.get("expect", {}) if isinstance(case, dict) else {}
        question = (case.get("question") or r.get("question") or "")
        should_refuse = bool(expect.get("should_refuse", False))
        is_refused = REFUSE_PREFIX in answer
        is_high_risk = any(w in question for w in HIGH_RISK_WORDS) or any(w in category for w in HIGH_RISK_WORDS)
        has_risky_commitment = any(p in answer for p in RISKY_COMMITMENTS)

        if should_refuse:
            refusal_total += 1
            if is_refused:
                refusal_ok += 1

        if is_high_risk:
            high_risk_total += 1
            if (not has_risky_commitment) and (is_refused or ("依据" in answer or "规则" in answer or "建议" in answer)):
                high_risk_ok += 1

        # 业务可参考值：不是只看关键词命中；看回答是否可执行、可转人工、或明确拒答。
        useful_total += 1
        useful_hit = (
            is_refused
            or any(x in answer for x in ["建议", "步骤", "先", "然后", "联系官方", "人工客服", "售后渠道"])
            or bool(r.get("ok"))
        )
        if useful_hit and not has_risky_commitment:
            useful_ok += 1

        if not r.get("ok"):
            fail_distribution[category] += 1

    return {
        "total": total,
        "keyword_pass_rate": safe_rate(keyword_pass, total),
        "avg_latency_s": avg_latency,
        "refusal_correct_rate": safe_rate(refusal_ok, refusal_total),
        "refusal_sample_count": refusal_total,
        "high_risk_compliance_rate": safe_rate(high_risk_ok, high_risk_total),
        "high_risk_sample_count": high_risk_total,
        "business_useful_rate": safe_rate(useful_ok, useful_total),
        "fail_distribution_by_category": dict(fail_distribution),
    }


def main():
    parser = argparse.ArgumentParser(description="对比 OFF/ON 的业务价值指标")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--off-report", required=True)
    parser.add_argument("--on-report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    case_map = load_cases(args.cases)
    with open(args.off_report, "r", encoding="utf-8") as f:
        off = json.load(f)
    with open(args.on_report, "r", encoding="utf-8") as f:
        on = json.load(f)

    off_m = summarize(off, case_map)
    on_m = summarize(on, case_map)
    delta = {
        "keyword_pass_rate": round(on_m["keyword_pass_rate"] - off_m["keyword_pass_rate"], 4),
        "avg_latency_s": round(on_m["avg_latency_s"] - off_m["avg_latency_s"], 4),
        "refusal_correct_rate": round(on_m["refusal_correct_rate"] - off_m["refusal_correct_rate"], 4),
        "high_risk_compliance_rate": round(on_m["high_risk_compliance_rate"] - off_m["high_risk_compliance_rate"], 4),
        "business_useful_rate": round(on_m["business_useful_rate"] - off_m["business_useful_rate"], 4),
    }

    output = {
        "input": {
            "cases": args.cases,
            "off_report": args.off_report,
            "on_report": args.on_report,
        },
        "metrics": {
            "off": off_m,
            "on": on_m,
            "delta_on_minus_off": delta,
        },
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(args.output)


if __name__ == "__main__":
    main()

