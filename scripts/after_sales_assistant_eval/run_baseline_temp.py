
#!/usr/bin/env python3
# coding: utf-8
import json
import os
import sys
from pathlib import Path

# 切换到脚本目录
SCRIPT_DIR = Path("/home/tlx/projects/MaxKB/scripts/after_sales_assistant_eval")
os.chdir(SCRIPT_DIR)
sys.path.insert(0, str(SCRIPT_DIR))

# 读取本地配置
with open(SCRIPT_DIR / "local_secrets.json", encoding="utf-8") as f:
    data = json.load(f)

# 设置环境变量
os.environ["MAXKB_BASE"] = str(data.get("maxkb_base", "http://localhost:8080")).rstrip("/")
os.environ["MAXKB_CHAT_PATH"] = str(data.get("maxkb_chat_path", "/chat"))
os.environ["MAXKB_APP_ID"] = str(data.get("maxkb_app_id", "")).strip()
os.environ["MAXKB_API_KEY"] = str(data.get("maxkb_api_key", "")).strip()

# 运行评测
import run_eval
sys.argv = [
    "run_eval.py",
    str(SCRIPT_DIR / "cases_v3.json"),
    "-o",
    "/mnt/c/Users/tlx/Desktop/baseline_round1.json",
]

if __name__ == "__main__":
    raise SystemExit(run_eval.main())

