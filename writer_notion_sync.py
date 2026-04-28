#!/usr/bin/env python3
"""
writer_notion_sync.py
ライターがpost-queue.mdに投稿を追加した後に実行する。

処理:
1. post-queue.mdを読み込み、未同期の投稿を抽出
2. Notion DBに各投稿を追加
   - 投稿日時 → title列
   - 本投稿（「（以下コメント欄）」より前） → 本投稿列
   - ツリー投稿（「（以下コメント欄）」より後） → ツリー投稿列
   - ステータス → 「未編集」
3. 同期済みIDをJSONファイルに記録（重複防止）
4. Slack通知（Notion URLつき）

使い方:
  python3 writer_notion_sync.py [生成本数]
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List

BASE = Path(__file__).resolve().parent
NOTION_DB_ID    = "3508be18-7f31-80af-ad02-d3eb16f9452e"
NOTION_DB_URL   = "https://www.notion.so/DB-3508be187f3180588e3eebb8681f110d"
SYNCED_IDS_FILE = BASE / "notion-db-synced-ids.json"
JST             = timezone(timedelta(hours=9))

# プロパティ名（実際のNotion DB列名）
PROP_TITLE  = "投稿日時"
PROP_MAIN   = "本投稿"
PROP_TREE   = "ツリー投稿"
PROP_STATUS = "ステータス（未編集／編集済み／投稿済み）"

# .env 読み込み
env: dict = {}
for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip()

NOTION_API_KEY    = env.get("NOTION_API_KEY", "")
SLACK_WEBHOOK_URL = env.get("SLACK_WEBHOOK_URL", "")

QUEUE_FIELD_STARTS = [
    "id:", "型：", "テーマ：", "予定投稿日時：", "PR：",
    "楽天商品名：", "楽天URL：", "品質スコア：",
    "承認ステータス：", "本文：",
]


# ── post-queue.md パーサー ───────────────────────────────────

def parse_queue(text: str) -> List[dict]:
    posts = []
    current: List[str] = []
    in_code = False

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.strip() == "---":
            if current:
                block = "\n".join(current).strip()
                if "id:" in block:
                    p = _parse_post_block(block)
                    if p:
                        posts.append(p)
            current = []
        else:
            current.append(line)

    if current:
        block = "\n".join(current).strip()
        if "id:" in block:
            p = _parse_post_block(block)
            if p:
                posts.append(p)

    return posts


def _parse_post_block(block: str) -> Optional[dict]:
    post: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("本文："):
            i += 1
            body_lines = []
            while i < len(lines) and not any(lines[i].startswith(f) for f in QUEUE_FIELD_STARTS):
                body_lines.append(lines[i])
                i += 1
            post["body"] = "\n".join(body_lines).strip()
            continue
        if line.startswith("id:"):
            post["id"] = line[3:].strip()
        elif line.startswith("予定投稿日時："):
            post["date"] = line.split("：", 1)[1].strip()
        i += 1

    if "id" not in post:
        return None

    # 本文を「（以下コメント欄）」で分割
    body = post.get("body", "")
    if "（以下コメント欄）" in body:
        parts = body.split("（以下コメント欄）", 1)
        post["main_text"] = parts[0].strip()
        post["tree_text"] = parts[1].strip()
    else:
        post["main_text"] = body
        post["tree_text"] = ""

    return post


# ── 同期済みIDの管理 ────────────────────────────────────────

def load_synced_ids() -> set:
    if SYNCED_IDS_FILE.exists():
        return set(json.loads(SYNCED_IDS_FILE.read_text(encoding="utf-8")))
    return set()


def save_synced_ids(ids: set) -> None:
    SYNCED_IDS_FILE.write_text(
        json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Notion API ───────────────────────────────────────────────

def notion_create_page(main_text: str, tree_text: str, date_str: str) -> Optional[str]:
    """Notion DBに1件追加。成功時はNotion URLを返す。"""
    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            PROP_TITLE: {
                "title": [{"type": "text", "text": {"content": date_str}}]
            },
            PROP_MAIN: {
                "rich_text": [{"type": "text", "text": {"content": main_text}}]
            },
            PROP_TREE: {
                "rich_text": [{"type": "text", "text": {"content": tree_text}}]
            },
            PROP_STATUS: {
                "rich_text": [{"type": "text", "text": {"content": "未編集"}}]
            },
        },
    }

    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
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
            return result.get("url", "")
    except urllib.error.HTTPError as e:
        print(f"  [Notion] HTTP {e.code}: {e.read().decode()[:300]}")
        return None
    except Exception as e:
        print(f"  [Notion] エラー: {e}")
        return None


# ── Slack 通知 ───────────────────────────────────────────────

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
        print("Slack通知を送信しました")
    except Exception as e:
        print(f"[Slack] 通知エラー: {e}")


# ── メイン ───────────────────────────────────────────────────

def main(post_count: int = 10) -> None:
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    print(f"=== ライター→Notion同期: {now_str} ===")

    # post-queue.md を読み込む
    queue_file = BASE / "post-queue.md"
    if not queue_file.exists():
        print("ERROR: post-queue.md が見つかりません")
        return

    all_posts = parse_queue(queue_file.read_text(encoding="utf-8"))
    synced_ids = load_synced_ids()

    # 未同期の投稿のみ対象
    new_posts = [p for p in all_posts if p["id"] not in synced_ids]
    print(f"未同期投稿: {len(new_posts)}件")

    if not new_posts:
        print("同期対象なし。")
        # それでもSlackには報告
        _send_slack_report(post_count, 0, now_str)
        return

    success_ids = []
    fail_count = 0

    for post in new_posts:
        pid       = post["id"]
        date_str  = post.get("date", "未設定")
        main_text = post.get("main_text", "")
        tree_text = post.get("tree_text", "")

        print(f"  [{pid}] {date_str} - {main_text[:30]}...")
        page_url = notion_create_page(main_text, tree_text, date_str)

        if page_url is not None:
            success_ids.append(pid)
            synced_ids.add(pid)
            print(f"  ✅ Notion追加: {page_url}")
        else:
            fail_count += 1
            print(f"  ❌ Notion追加失敗")

    # 同期済みIDを保存
    save_synced_ids(synced_ids)

    print(f"同期完了: 成功{len(success_ids)}件 / 失敗{fail_count}件")
    _send_slack_report(post_count, len(success_ids), now_str)


def _send_slack_report(post_count: int, synced_count: int, now_str: str) -> None:
    """Slackにライター完了報告（Notion URLつき）を送信"""
    lines = [
        "ライター作業が終わりました",
        f"翌日投稿{post_count}本を生成しました",
        f"完了時刻: {now_str}",
        f"Notion DB: {NOTION_DB_URL}",
    ]
    if synced_count > 0:
        lines.append(f"Notion追加: {synced_count}件")
    slack_notify("\n".join(lines))


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    main(count)
