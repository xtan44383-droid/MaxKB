#!/bin/bash
cd /home/tlx/projects/MaxKB/scripts/after_sales_assistant_eval
export MAXKB_BASE=http://127.0.0.1:8080
export MAXKB_CHAT_PATH=/chat
export MAXKB_APP_ID=019dd098-7fbd-7f61-a017-f5a541697702
export MAXKB_API_KEY=agent-11e0837033c60cf139d6df35505da7b7
exec ../../.venv/bin/python run_eval.py ./cases_v3.json -o /mnt/c/Users/tlx/Desktop/baseline_round1.json
