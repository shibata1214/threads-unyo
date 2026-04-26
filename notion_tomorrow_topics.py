#!/usr/bin/env python3
"""
notion_tomorrow_topics.py
毎朝6時に「明日投稿するネタ」をNotionページに更新する

使い方:
  python3 notion_tomorrow_topics.py              # 明日の日付で実行
  python3 notion_tomorrow_topics.py 2026-04-20   # 指定日で実行（テスト用）
"""

import sys
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent
# https://www.notion.so/3438be187f31818c800dfcf77e260af8
PAGE_ID = "3438be18-7f31-818c-800d-fcf77e260af8"
CACHE_FILE = BASE / "notion-topics-cache.json"

# .env からAPIキーを読み込む
env_path = BASE / ".env"
API_KEY = None
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("NOTION_API_KEY="):
            API_KEY = line.split("=", 1)[1].strip()

if not API_KEY:
    print("ERROR: NOTION_API_KEY が .env に見つかりません")
    sys.exit(1)


# ──────────────────────────────────────────────────────
# Notion API
# ──────────────────────────────────────────────────────

def notion_request(method, path, payload=None):
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  Notion API エラー {e.code}: {body}")
        return None


def get_page_blocks(page_id):
    result = notion_request("GET", f"/blocks/{page_id}/children?page_size=100")
    return result.get("results", []) if result else []


def delete_block(block_id):
    notion_request("DELETE", f"/blocks/{block_id}")


def append_blocks(page_id, children):
    # Notion は一度に100ブロックまで
    for i in range(0, len(children), 100):
        notion_request("PATCH", f"/blocks/{page_id}/children", {"children": children[i:i+100]})


def rich_text(text):
    chunks = []
    text = str(text)
    while text:
        chunk, text = text[:2000], text[2000:]
        chunks.append({"type": "text", "text": {"content": chunk}})
    return chunks or [{"type": "text", "text": {"content": ""}}]


# ──────────────────────────────────────────────────────
# post-queue.md パーサー
# ──────────────────────────────────────────────────────

QUEUE_FIELD_STARTS = [
    "id:", "型：", "テーマ：", "予定投稿日時：", "PR：", "楽天商品名：",
    "楽天URL：", "品質スコア：", "承認ステータス：", "ツリー投稿：", "ツリー本文：", "本文："
]


def split_into_blocks(text):
    lines = text.splitlines()
    blocks = []
    current = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.strip() == "---":
            if current:
                content = "\n".join(current).strip()
                if "id:" in content:
                    blocks.append(content)
            current = []
        else:
            current.append(line)
    if current:
        content = "\n".join(current).strip()
        if "id:" in content:
            blocks.append(content)
    return blocks


def parse_queue_block(block):
    post = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("本文："):
            i += 1
            body_lines = []
            while i < len(lines):
                nxt = lines[i]
                if any(nxt.startswith(f) for f in QUEUE_FIELD_STARTS):
                    break
                body_lines.append(nxt)
                i += 1
            post["body"] = "\n".join(body_lines).strip()
            continue
        if line.startswith("id:"):
            post["id"] = line[3:].strip()
        elif line.startswith("テーマ："):
            post["theme"] = line.split("：", 1)[1].strip()
        elif line.startswith("型："):
            post["type"] = line.split("：", 1)[1].strip()
        elif line.startswith("予定投稿日時："):
            raw = line.split("：", 1)[1].strip()
            m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
            post["scheduled_date"] = m.group(1) if m else None
        elif line.startswith("承認ステータス："):
            post["status"] = line.split("：", 1)[1].strip()
        elif line.startswith("PR："):
            post["pr"] = line.split("：", 1)[1].strip()
        elif line.startswith("楽天商品名："):
            post["rakuten"] = line.split("：", 1)[1].strip()
        i += 1
    return post if "id" in post else None


# ──────────────────────────────────────────────────────
# キャッシュ（ユーザー削除ネタを追跡）
# ──────────────────────────────────────────────────────

def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {"shown_ids": [], "user_deleted_ids": []}


def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


# ──────────────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────────────

def main():
    # 対象日（デフォルト：明日）
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"📅 対象日: {target_date}")

    # post-history.md から投稿済みIDを収集
    history_file = BASE / "post-history.md"
    posted_ids = set()
    if history_file.exists():
        history_text = history_file.read_text("utf-8")
        posted_ids = set(re.findall(r"^id:\s*(\S+)", history_text, re.MULTILINE))
    print(f"  投稿済みID: {len(posted_ids)}件")

    # post-queue.md から対象日の投稿を収集
    queue_file = BASE / "post-queue.md"
    tomorrow_posts = []
    if queue_file.exists():
        queue_text = queue_file.read_text("utf-8")
        all_posts = [
            p for b in split_into_blocks(queue_text)
            if (p := parse_queue_block(b))
        ]
        tomorrow_posts = [p for p in all_posts if p.get("scheduled_date") == target_date]
    print(f"  キュー内の{target_date}分: {len(tomorrow_posts)}件")

    # キャッシュ読み込み
    cache = load_cache()
    shown_ids = set(cache["shown_ids"])
    user_deleted_ids = set(cache["user_deleted_ids"])

    # 現在のNotionページブロックを取得して表示中のIDを抽出
    print("  Notionページを読み込み中...")
    current_blocks = get_page_blocks(PAGE_ID)
    currently_on_notion = set()
    for block in current_blocks:
        # ブロックテキストからIDを抽出（例: [001] テーマ名）
        for btype in ["bulleted_list_item", "paragraph", "heading_2", "heading_3"]:
            if btype in block:
                for rt in block[btype].get("rich_text", []):
                    text = rt.get("text", {}).get("content", "")
                    m = re.search(r"\[(\d+)\]", text)
                    if m:
                        currently_on_notion.add(m.group(1))

    # ユーザー削除を検出（以前表示したが今はNotionにない & 投稿済みでもない）
    newly_deleted = shown_ids - currently_on_notion - posted_ids
    user_deleted_ids.update(newly_deleted)
    if newly_deleted:
        print(f"  ユーザー削除を検出: {newly_deleted}")

    # 表示すべき投稿を決定
    to_show = []
    for post in tomorrow_posts:
        pid = post["id"]
        if pid in posted_ids:
            print(f"  スキップ（投稿済み）: [{pid}] {post.get('theme', '')}")
            continue
        if pid in user_deleted_ids:
            print(f"  スキップ（ユーザー削除）: [{pid}] {post.get('theme', '')}")
            continue
        to_show.append(post)

    print(f"  表示するネタ: {len(to_show)}件")

    # Notionページを更新
    print("  既存ブロックを削除中...")
    for block in current_blocks:
        delete_block(block["id"])

    # 新しいブロックを構築
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": rich_text(f"📋 {dt.month}/{dt.day}（明日）投稿するネタ")},
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": rich_text(f"自動更新: {now_str}　｜　{len(to_show)}件")},
        },
        {
            "object": "block",
            "type": "divider",
            "divider": {},
        },
    ]

    if to_show:
        for post in to_show:
            pid = post["id"]
            theme = post.get("theme", "（テーマ不明）")
            ptype = post.get("type", "")
            pr = post.get("pr", "なし")
            rakuten = post.get("rakuten", "")

            label = f"[{pid}] {theme}"
            if ptype:
                label += f"  ／  {ptype}"
            if pr == "あり" and rakuten and rakuten != "なし":
                label += f"  🛍️ {rakuten}"

            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich_text(label)},
            })
    else:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": rich_text("（明日の予定投稿はありません）")},
        })

    append_blocks(PAGE_ID, blocks)

    # キャッシュ更新
    cache["shown_ids"] = list(shown_ids | {p["id"] for p in to_show})
    cache["user_deleted_ids"] = list(user_deleted_ids)
    save_cache(cache)

    print(f"✅ Notionを更新しました（{len(to_show)}件表示）")


if __name__ == "__main__":
    main()
