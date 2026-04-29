#!/usr/bin/env python3
"""
pm_overdue_check.py
PM部：編集済み投稿の未投稿チェック（13分ごとに実行）

処理:
1. Notion DBから「編集済み」ステータスの投稿を取得
2. 予定投稿日時が現在時刻を過ぎているものを抽出
3. 結果をSlackに報告（問題あり・なし両方）
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
PROP_TITLE = "投稿日時"

# .env 読み込み
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


def query_notion(filter_body: dict) -> list:
    data = json.dumps(filter_body, ensure_ascii=False).encode()
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
            return json.loads(r.read()).get("results", [])
    except Exception as e:
        print(f"[Notion] エラー: {e}")
        return []


def parse_scheduled_time(date_str: str):
    """予定投稿日時の文字列をdatetimeに変換。未設定・解析不能はNoneを返す。"""
    date_str = date_str.strip()
    if not date_str or date_str in ("未設定", "-", ""):
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=JST)
        except ValueError:
            continue
    return None


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
    now = datetime.now(JST)
    now_str = now.strftime("%Y-%m-%d %H:%M")

    pages = query_notion({
        "filter": {
            "property": PROP_STATUS,
            "rich_text": {"equals": "編集済み"}
        }
    })

    overdue = []
    for page in pages:
        title_list = page.get("properties", {}).get(PROP_TITLE, {}).get("title", [])
        date_str = title_list[0]["text"]["content"] if title_list else ""
        scheduled = parse_scheduled_time(date_str)
        if scheduled and scheduled < now:
            overdue.append({
                "date": date_str,
                "url": page.get("url", ""),
            })

    if overdue:
        lines = [
            f"⚠️ [PM] 編集済みなのに時間を過ぎても未投稿の投稿が {len(overdue)}件 あります",
            f"確認時刻: {now_str} JST",
            "",
        ]
        for item in overdue:
            lines.append(f"・{item['date']}　{item['url']}")
        slack_notify("\n".join(lines))
        print(f"[{now_str}] 未投稿アラート: {len(overdue)}件")
    else:
        slack_notify(f"[PM] 編集済み未投稿チェック: 問題なし（{now_str} JST）")
        print(f"[{now_str}] 未投稿チェック: 問題なし")


if __name__ == "__main__":
    main()
