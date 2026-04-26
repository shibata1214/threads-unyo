#!/usr/bin/env python3
"""
notion_sync_all.py
Claudeが作業を終えるたびに自動実行される。
以下のファイルをNotionに同期する：
  - post-queue.md    → 「📋 投稿待機列」ページ
  - next-topics.md   → 「🗒 次のテーマ」ページ
  - analysis-latest.md → 「📊 最新分析」ページ
"""

import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE = Path("/Users/mina/スレッズ")
PARENT_PAGE_ID = "3428be18-7f31-80ff-94c8-fb23130319a4"  # スレッズ投稿ストック
REGISTRY_FILE = BASE / "notion-sync-registry.json"

# .envからAPIキーを読む
API_KEY = None
for line in (BASE / ".env").read_text().splitlines():
    if line.startswith("NOTION_API_KEY="):
        API_KEY = line.split("=", 1)[1].strip()

if not API_KEY:
    print("ERROR: NOTION_API_KEY が .env に見つかりません", file=sys.stderr)
    sys.exit(1)


# ── Notion API ─────────────────────────────────────────────

def notion_req(method, path, payload=None):
    req = urllib.request.Request(
        f"https://api.notion.com/v1{path}",
        data=json.dumps(payload, ensure_ascii=False).encode() if payload else None,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  API error {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return None


def rt(text, bold=False, color=None):
    chunks = []
    text = str(text)
    while text:
        chunk, text = text[:2000], text[2000:]
        item = {"type": "text", "text": {"content": chunk}}
        ann = {}
        if bold:
            ann["bold"] = True
        if color:
            ann["color"] = color
        if ann:
            item["annotations"] = ann
        chunks.append(item)
    return chunks or [{"type": "text", "text": {"content": ""}}]


def get_blocks(page_id):
    r = notion_req("GET", f"/blocks/{page_id}/children?page_size=100")
    return r.get("results", []) if r else []


def delete_block(block_id):
    notion_req("DELETE", f"/blocks/{block_id}")


def append_blocks(page_id, children):
    for i in range(0, len(children), 100):
        notion_req("PATCH", f"/blocks/{page_id}/children", {"children": children[i:i+100]})


def create_page(title, emoji, children):
    r = notion_req("POST", "/pages", {
        "parent": {"page_id": PARENT_PAGE_ID},
        "icon": {"type": "emoji", "emoji": emoji},
        "properties": {"title": [{"text": {"content": title}}]},
        "children": children[:100],
    })
    if not r:
        return None, None
    page_id = r.get("id", "")
    # 100件超は追記
    if len(children) > 100:
        append_blocks(page_id, children[100:])
    return r.get("url", ""), page_id


def load_registry():
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text("utf-8"))
    return {}


def save_registry(reg):
    REGISTRY_FILE.write_text(json.dumps(reg, ensure_ascii=False, indent=2), "utf-8")


def update_page(page_id, children):
    """既存ページのブロックを全部消してから書き直す"""
    for b in get_blocks(page_id):
        delete_block(b["id"])
    append_blocks(page_id, children)


def para(text, bold=False, color=None):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": rt(text, bold=bold, color=color)}}


def h2(text):
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": rt(text)}}


def h3(text):
    return {"object": "block", "type": "heading_3",
            "heading_3": {"rich_text": rt(text)}}


def divider():
    return {"object": "block", "type": "divider", "divider": {}}


def bullet(text, bold=False):
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": rt(text, bold=bold)}}


def code_block(text):
    # コードブロック（1ブロック最大2000文字なので分割）
    blocks = []
    while text:
        chunk, text = text[:2000], text[2000:]
        blocks.append({
            "object": "block", "type": "code",
            "code": {"rich_text": rt(chunk), "language": "plain text"},
        })
    return blocks


# ── post-queue.md パーサー ─────────────────────────────────

QUEUE_FIELD_STARTS = [
    "id:", "型：", "テーマ：", "予定投稿日時：", "PR：",
    "楽天商品名：", "楽天URL：", "品質スコア：",
    "承認ステータス：", "ツリー投稿：", "ツリー本文：", "本文：",
]


def parse_queue(text):
    posts = []
    current = []
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
                    posts.append(parse_one_post(block))
            current = []
        else:
            current.append(line)
    if current:
        block = "\n".join(current).strip()
        if "id:" in block:
            posts.append(parse_one_post(block))
    return [p for p in posts if p]


def parse_one_post(block):
    post = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("本文："):
            i += 1
            body = []
            while i < len(lines) and not any(lines[i].startswith(f) for f in QUEUE_FIELD_STARTS):
                body.append(lines[i])
                i += 1
            post["body"] = "\n".join(body).strip()
            continue
        if line.startswith("ツリー本文："):
            i += 1
            tree = []
            while i < len(lines) and not any(lines[i].startswith(f) for f in QUEUE_FIELD_STARTS):
                tree.append(lines[i])
                i += 1
            post["tree"] = "\n".join(tree).strip()
            continue
        if line.startswith("id:"):
            post["id"] = line[3:].strip()
        elif line.startswith("テーマ："):
            post["theme"] = line.split("：", 1)[1].strip()
        elif line.startswith("PR："):
            post["pr"] = line.split("：", 1)[1].strip()
        elif line.startswith("楽天商品名："):
            post["rakuten"] = line.split("：", 1)[1].strip()
        elif line.startswith("承認ステータス："):
            post["status"] = line.split("：", 1)[1].strip()
        elif line.startswith("予定投稿日時："):
            post["date"] = line.split("：", 1)[1].strip()
        elif line.startswith("品質スコア："):
            post["score"] = line.split("：", 1)[1].strip()
        i += 1
    return post if "id" in post else None


def build_queue_blocks(posts):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    pending = [p for p in posts if p.get("status", "") != "OK"]
    posted = [p for p in posts if p.get("status", "") == "OK"]

    blocks = [
        h2("📋 投稿待機列"),
        para(f"自動同期: {now}　｜　待機中 {len(pending)}本", bold=True),
        para("「承認ステータス：OK」に変えると投稿されます"),
        divider(),
    ]

    if pending:
        blocks.append(h3(f"⏳ 待機中（{len(pending)}本）"))
        for p in pending:
            pid = p.get("id", "?")
            theme = p.get("theme", "（テーマ不明）")
            pr = p.get("pr", "なし")
            score = p.get("score", "")
            date = p.get("date", "未設定")
            rakuten = p.get("rakuten", "")

            label = f"[{pid}] {theme}"
            if pr == "あり" and rakuten and rakuten != "なし":
                label += f"  🛍️ {rakuten}"
            if score:
                label += f"  {score}"
            label += f"  📅 {date}"

            blocks.append(bullet(label, bold=(pr == "あり")))

            body = p.get("body", "")
            tree = p.get("tree", "")
            if body:
                full = body
                if tree:
                    full += f"\n\n（以下コメント欄）\n\n{tree}"
                blocks.extend(code_block(full))

            blocks.append(divider())

    if posted:
        blocks.append(h3(f"✅ OK済み（{len(posted)}本）"))
        for p in posted:
            blocks.append(bullet(f"[{p['id']}] {p.get('theme','')}", bold=False))

    return blocks


# ── next-topics.md → Notionブロック ───────────────────────

def build_topics_blocks(text):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    blocks = [
        h2("🗒 次のテーマ・7回訴求プラン"),
        para(f"自動同期: {now}", bold=True),
        divider(),
    ]
    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.startswith("# 次に書くテーマ"):
            continue
        if stripped.startswith("## "):
            blocks.append(h2(stripped[3:]))
        elif stripped.startswith("### "):
            blocks.append(h3(stripped[4:]))
        elif stripped.startswith("#### "):
            blocks.append(h3(stripped[5:]))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append(bullet(stripped[2:]))
        elif stripped.startswith("<!--") or stripped == "-->":
            continue
        elif stripped == "---":
            blocks.append(divider())
        elif stripped:
            blocks.append(para(stripped))
    return blocks


# ── analysis-latest.md → Notionブロック ──────────────────

def build_analysis_blocks(text):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    blocks = [
        h2("📊 最新分析結果"),
        para(f"自動同期: {now}", bold=True),
        divider(),
    ]
    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.startswith("# 最新分析"):
            continue
        if stripped.startswith("## "):
            blocks.append(h2(stripped[3:]))
        elif stripped.startswith("### "):
            blocks.append(h3(stripped[4:]))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append(bullet(stripped[2:]))
        elif stripped == "---":
            blocks.append(divider())
        elif stripped:
            blocks.append(para(stripped))
    return blocks


# ── メイン ────────────────────────────────────────────────

def sync_page(reg, key, title, emoji, blocks):
    if key in reg:
        print(f"  更新: {title} ...", end=" ", flush=True)
        update_page(reg[key], blocks)
        print("✅")
    else:
        print(f"  新規作成: {title} ...", end=" ", flush=True)
        url, page_id = create_page(title, emoji, blocks)
        if page_id:
            reg[key] = page_id
            print(f"✅ {url}")
        else:
            print("❌ 失敗")


def main():
    reg = load_registry()

    # 1. 投稿待機列
    queue_text = (BASE / "post-queue.md").read_text("utf-8")
    posts = parse_queue(queue_text)
    sync_page(reg, "queue", "📋 投稿待機列", "📋", build_queue_blocks(posts))

    # 2. 次のテーマ
    topics_text = (BASE / "next-topics.md").read_text("utf-8")
    sync_page(reg, "topics", "🗒 次のテーマ・7回訴求プラン", "🗒", build_topics_blocks(topics_text))

    # 3. 最新分析
    analysis_text = (BASE / "analysis-latest.md").read_text("utf-8")
    sync_page(reg, "analysis", "📊 最新分析結果", "📊", build_analysis_blocks(analysis_text))

    save_registry(reg)
    print("🎉 Notion同期完了")


if __name__ == "__main__":
    main()
