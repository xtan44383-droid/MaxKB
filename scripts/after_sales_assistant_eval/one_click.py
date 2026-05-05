#!/usr/bin/env python3
# coding: utf-8
"""
一键跑评估：从同目录 local_secrets.json 读地址、应用 ID、API 密钥，再调用 run_eval。
使用：在本目录执行  ../../.venv/bin/python one_click.py
说明全文：docs/after_sales_assistant/11_工作流联调_自动评估脚本说明.md

local_secrets.json 已加入 .gitignore，勿把真实密钥提交到 Git。
若接口返回 401，请在 MaxKB 应用设置里使用「应用 API 密钥」
（仅支持 application- 与 agent- 开头，与 MaxKB 应用里创建的密钥一致）。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECRETS = HERE / "local_secrets.json"
CASES = HERE / "eval_cases.json"
REPORT = HERE / "report.json"


def main() -> int:
    if not SECRETS.is_file():
        print(f"缺少 {SECRETS}，请复制 local_secrets.example.json 为 local_secrets.json 并填写。", file=sys.stderr)
        return 2
    ex = HERE / "eval_cases.example.json"
    if not CASES.is_file() and ex.is_file():
        shutil.copy2(ex, CASES)
    if not CASES.is_file():
        print(f"缺少 {CASES} 且无 eval_cases.example.json 可复制。", file=sys.stderr)
        return 2
    with open(SECRETS, encoding="utf-8") as f:
        data = json.load(f)
    os.environ["MAXKB_BASE"] = str(data.get("maxkb_base", "http://localhost:8080")).rstrip("/")
    os.environ["MAXKB_CHAT_PATH"] = str(data.get("maxkb_chat_path", "/chat"))
    os.environ["MAXKB_APP_ID"] = str(data.get("maxkb_app_id", "")).strip()
    os.environ["MAXKB_API_KEY"] = str(data.get("maxkb_api_key", "")).strip()
    os.chdir(HERE)
    sys.path.insert(0, str(HERE))
    sys.argv = [
        "run_eval.py",
        str(CASES),
        "-o",
        str(REPORT),
    ]
    import run_eval  # noqa: E402

    return run_eval.main()


if __name__ == "__main__":
    raise SystemExit(main())
