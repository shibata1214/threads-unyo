#!/usr/bin/env python3
"""
Notion 投稿日次ページ作成・更新スクリプト（テーブル形式）

post-history.md + post_HHMM.sh ファイルから日付別にNotionへ保存する。
.shファイルから実際の投稿全文を取得し、予約投稿も表示する。
既存ページは上書き（アーカイブ→再作成）。

使い方:
  python3 notion_posts_to_notion.py              # 全日付
  python3 notion_posts_to_notion.py 2026-04-19   # 特定日のみ
"""

import sys
import json
import re
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PARENT_PAGE_ID = "3448be18-7f31-8055-a8d7-e907cc9e46f2"
BASE = Path(__file__).parent
REGISTRY_FILE = BASE / "notion-pages-registry.json"

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
# レジストリ（ページID管理）
# ──────────────────────────────────────────────────────

def load_registry():
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text("utf-8"))
    return {}


def save_registry(registry):
    REGISTRY_FILE.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def archive_page(page_id):
    """Notionページをアーカイブ（上書き前に削除）"""
    data = json.dumps({"archived": True}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req):
            return True
    except Exception:
        return False


# ──────────────────────────────────────────────────────
# .shファイルスキャン（実際の投稿全文を取得）
# ──────────────────────────────────────────────────────

def scan_sh_posts(date_str):
    """
    post_HHMM.sh ファイルをスキャンして指定日の投稿を返す。
    ログに「全完了」があれば投稿済み、なければ予約中。
    """
    posts = []

    for sh_file in sorted(BASE.glob("post_????.sh")):
        m = re.match(r"post_(\d{4})\.sh", sh_file.name)
        if not m:
            continue
        time_code = m.group(1)
        time_str = f"{time_code[:2]}:{time_code[2:]}"

        try:
            content = sh_file.read_text("utf-8")
        except Exception:
            continue

        # このスクリプトが date_str の投稿か確認
        date_m = re.search(r"投稿日時：(\d{4}-\d{2}-\d{2})", content)
        if date_m:
            if date_m.group(1) != date_str:
                continue
        else:
            # $(date...) を使う動的スクリプトは今日分として扱う
            from datetime import date as _date
            if "$(date" not in content:
                continue
            if date_str != _date.today().strftime("%Y-%m-%d"):
                continue

        # テーマ（先頭コメントから）
        theme_m = re.search(r"^# \d+:\d+投稿スクリプト：(.+)$", content, re.MULTILINE)
        theme = theme_m.group(1).strip() if theme_m else f"{time_str}の投稿"

        # MAIN_TEXT（単一引用符内）
        main_m = re.search(r"MAIN_TEXT='([^']*)'", content, re.DOTALL)
        main_text = main_m.group(1) if main_m else ""

        # TREE_TEXT（単一引用符内）
        tree_m = re.search(r"TREE_TEXT='([^']*)'", content, re.DOTALL)
        tree_text = tree_m.group(1) if tree_m else ""

        # PR情報
        pr = "なし"
        rakuten = ""
        if "PR" in content and ("楽天" in content or "rakuten" in content.lower()):
            pr = "あり"
            rak_m = re.search(r"楽天商品名：(.+)", content)
            if rak_m:
                rakuten = rak_m.group(1).strip()

        # 投稿済みかチェック（ログファイルに「全完了」があれば完了）
        already_done = False
        for suffix in ["", "_nohup"]:
            log_file = BASE / f"post_{time_code}{suffix}.log"
            if log_file.exists():
                try:
                    log_text = log_file.read_text("utf-8", errors="replace")
                    if "✅ 全完了" in log_text or "🎉 全処理完了" in log_text:
                        already_done = True
                        break
                except Exception:
                    pass

        posts.append({
            "date": date_str,
            "time": time_str,
            "theme": theme,
            "matched_body": main_text,
            "matched_tree": tree_text,
            "pr": pr,
            "rakuten": rakuten,
            "scheduled": not already_done,
            "source": "sh",
        })

    return posts


# ──────────────────────────────────────────────────────
# post-history.md パーサー
# ──────────────────────────────────────────────────────

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


def parse_history_block(block):
    post = {}
    for line in block.splitlines():
        if line.startswith("id:"):
            post["id"] = line[3:].strip()
        elif line.startswith("投稿日時："):
            raw = line.split("：", 1)[1].strip()
            m = re.match(r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?", raw)
            if m:
                post["date"] = m.group(1)
                post["time"] = m.group(2) or ""
        elif line.startswith("テーマ："):
            post["theme"] = line.split("：", 1)[1].strip()
        elif line.startswith("本文（全文）："):
            post["full_text"] = line.split("：", 1)[1].strip()
        elif line.startswith("本文（先頭50文字）："):
            post["excerpt"] = line.split("：", 1)[1].strip()
        elif line.startswith("PR："):
            post["pr"] = line.split("：", 1)[1].strip()
        elif line.startswith("楽天商品名："):
            post["rakuten"] = line.split("：", 1)[1].strip()
        elif line.startswith("Threads投稿ID："):
            post["threads_id"] = line.split("：", 1)[1].strip()

    return post if "date" in post else None


# ──────────────────────────────────────────────────────
# Notion ブロック生成
# ──────────────────────────────────────────────────────

def rich_text(text, bold=False):
    chunks = []
    while text:
        chunk, text = text[:2000], text[2000:]
        item = {"type": "text", "text": {"content": chunk}}
        if bold:
            item["annotations"] = {"bold": True}
        chunks.append(item)
    return chunks or [{"type": "text", "text": {"content": ""}}]


def build_table(posts):
    rows = []

    # ヘッダー行
    rows.append({
        "object": "block",
        "type": "table_row",
        "table_row": {
            "cells": [
                rich_text("時間", bold=True),
                rich_text("投稿内容", bold=True),
            ]
        },
    })

    for post in posts:
        # 時間列
        time_str = post.get("time") or "—"
        if post.get("scheduled"):
            time_str = f"📅 {time_str} 予約"

        # 投稿全文（優先順位：full_text > matched_body > excerpt）
        body = (
            post.get("full_text")
            or post.get("matched_body")
            or post.get("excerpt", "")
        )
        tree = post.get("matched_tree", "")

        if tree:
            full_text = f"{body}\n\n（以下コメント欄）\n\n{tree}"
        else:
            full_text = body or post.get("theme", "（内容不明）")

        # PR商品を末尾に追記
        pr = post.get("pr", "")
        rakuten = post.get("rakuten", "")
        if pr == "あり" and rakuten and rakuten not in ("なし", ""):
            full_text += f"\n\n🛍️ PR商品：{rakuten}"

        rows.append({
            "object": "block",
            "type": "table_row",
            "table_row": {
                "cells": [
                    rich_text(time_str),
                    rich_text(full_text),
                ]
            },
        })

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 2,
            "has_column_header": True,
            "has_row_header": False,
            "children": rows,
        },
    }


# ──────────────────────────────────────────────────────
# Notion API
# ──────────────────────────────────────────────────────

def create_page(title, children):
    payload = {
        "parent": {"page_id": PARENT_PAGE_ID},
        "properties": {"title": [{"text": {"content": title}}]},
        "children": children,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return result.get("url", ""), result.get("id", "")
    except urllib.error.HTTPError as e:
        print(f"\n  ERROR {e.code}: {e.read().decode()}")
        return None, None


def format_title(date_str, count):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.year}.{dt.month}.{dt.day}（{count}投稿）"


# ──────────────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────────────

def main():
    filter_date = sys.argv[1] if len(sys.argv) > 1 else None

    # post-history.md をパース
    history_text = (BASE / "post-history.md").read_text("utf-8")
    history_posts = [
        p for b in split_into_blocks(history_text)
        if (p := parse_history_block(b))
    ]

    # 日付ごとに処理する日付リストを決定
    hist_dates = {p["date"] for p in history_posts if p.get("date")}

    if filter_date:
        target_dates = [filter_date]
    else:
        # 全日付（history + shファイル両方から）
        sh_dates = set()
        for sh_file in BASE.glob("post_????.sh"):
            try:
                content = sh_file.read_text("utf-8")
                dm = re.search(r"投稿日時：(\d{4}-\d{2}-\d{2})", content)
                if dm:
                    sh_dates.add(dm.group(1))
            except Exception:
                pass
        target_dates = sorted(hist_dates | sh_dates)

    if not target_dates:
        print("投稿データが見つかりませんでした")
        sys.exit(1)

    registry = load_registry()
    print(f"対象日数: {len(target_dates)}日分")

    for date_str in target_dates:
        # .shファイルから今日の投稿を取得
        sh_posts = scan_sh_posts(date_str)
        sh_by_time = {p["time"]: p for p in sh_posts}

        # post-history から今日の投稿を取得
        hist_posts = [p for p in history_posts if p.get("date") == date_str]

        # マージ：history投稿に.shの全文を付与
        merged = []
        hist_times = set()

        for hp in hist_posts:
            time = hp.get("time", "")
            hist_times.add(time)

            sh = sh_by_time.get(time)
            if sh and sh.get("matched_body"):
                # .shファイルの実際の文章を優先
                hp["matched_body"] = sh["matched_body"]
                hp["matched_tree"] = sh["matched_tree"]
                if not hp.get("rakuten") or hp.get("rakuten") == "なし":
                    hp["rakuten"] = sh.get("rakuten", "")
            # full_textがあればそちらを使う（post.mdの新フォーマット）

        merged.extend(hist_posts)

        # 予約中の.sh投稿（まだhistoryにないもの）を追加
        for sp in sh_posts:
            if sp.get("scheduled") and sp["time"] not in hist_times:
                merged.append(sp)

        if not merged:
            print(f"  スキップ: {date_str}（データなし）")
            continue

        # 時刻順にソート（時刻なしは後ろ）
        merged.sort(key=lambda p: p.get("time") or "99:99")

        title = format_title(date_str, len(merged))
        print(f"  更新中: {title} ...", end=" ", flush=True)

        # 既存ページをアーカイブ
        if date_str in registry:
            archive_page(registry[date_str])

        # 新ページ作成
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        scheduled_count = sum(1 for p in merged if p.get("scheduled"))
        posted_count = len(merged) - scheduled_count

        summary = f"{dt.year}年{dt.month}月{dt.day}日　投稿済み {posted_count}本"
        if scheduled_count:
            summary += f"　予約中 {scheduled_count}本"

        intro = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": rich_text(summary, bold=True)},
        }

        table = build_table(merged)
        url, page_id = create_page(title, [intro, table])

        if url:
            registry[date_str] = page_id
            save_registry(registry)
            print(f"✅ {url}")
        else:
            print("❌ 失敗")


if __name__ == "__main__":
    main()
