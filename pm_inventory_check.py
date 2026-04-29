#!/usr/bin/env python3
"""
pm_inventory_check.py
PM部：投稿在庫チェック（毎時実行）

処理:
1. Notion DBの「未編集」「編集済み」投稿数を取得
2. 合計10本以下ならSlackでライターに補充指示 + ライタートリガーを起動
3. 結果を常にSlackに報告
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
NOTION_DB_ID = "3508be18-7f31-80af-ad02-d3eb16f9452e"
PROP_STATUS = "ステータス（未編集／編集済み／投稿済み）"
WRITER_TRIGGER_ID = "trig_01SBczT3pfhbe2ibAtwGpYSx"

env: dict = {}
env_file = BASE / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

NOTION_API_KEY = env.get("NOTION_API_KEY", "")
SLACK_WEBHOOK_URL = env.get("SLACK_WEBHOOK_URL", "")


def count_notion_by_status(status: str) -> int:
    payload = {
        "filter": {
            "property": PROP_STATUS,
            "rich_text": {"equals": status}
        }
    }
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
        data=data,
        headers={
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            return len(result.get("results", []))
    except Exception as e:
        print(f"[Notion] エラー ({status}): {e}")
        return -1


def slack_notify(message: str) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    data = json.dumps({"text": message}).encode()
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[Slack] エラー: {e}")


def main():
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M")

    unedited = count_notion_by_status("未編集")
    edited = count_notion_by_status("編集済み")

    if unedited < 0 or edited < 0:
        slack_notify(f"[PM] 在庫チェック: Notion取得エラー（{now_str} JST）")
        return

    total = unedited + edited

    if total <= 10:
        message = (
            f"⚠️ [PM] 投稿在庫が残り {total}本 です（未編集:{unedited} + 編集済み:{edited}）\n"
            f"ライタートリガーを起動して補充します。\n"
            f"確認時刻: {now_str} JST"
        )
        slack_notify(message)
        print(f"[{now_str}] 在庫 {total}本 → ライター起動アラート送信")
    else:
        slack_notify(
            f"[PM] 在庫チェック: 残り {total}本（未編集:{unedited} + 編集済み:{edited}）問題なし（{now_str} JST）"
        )
        print(f"[{now_str}] 在庫チェック: {total}本 問題なし")


if __name__ == "__main__":
    main()
