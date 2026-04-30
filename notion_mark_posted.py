#!/usr/bin/env python3
"""
notion_mark_posted.py
Threadsに投稿済みのコンテンツをNotion DBで「投稿済み」に自動更新する。

処理:
1. Threads APIで最新投稿（最大25件）を取得
2. Notion DBから「未編集」「編集済み」のエントリを取得
3. 本文の冒頭50文字で照合し、一致したものを「投稿済み」に更新
4. 更新結果をSlackに報告
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
JST  = timezone(timedelta(hours=9))

NOTION_DB_ID = "3508be18-7f31-80af-ad02-d3eb16f9452e"
PROP_MAIN    = "本投稿"
PROP_STATUS  = "ステータス（未編集／編集済み／投稿済み）"

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

NOTION_API_KEY       = env.get("NOTION_API_KEY", "")
THREADS_USER_ID      = env.get("THREADS_USER_ID", "")
THREADS_ACCESS_TOKEN = env.get("THREADS_ACCESS_TOKEN", "")
SLACK_WEBHOOK_URL    = env.get("SLACK_WEBHOOK_URL", "")


def get_threads_posts(limit: int = 25) -> list:
    """Threads APIで最新投稿一覧を取得"""
    url = (
        f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
        f"?fields=id,text,timestamp&limit={limit}"
        f"&access_token={THREADS_ACCESS_TOKEN}"
    )
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data.get("data", [])
    except Exception as e:
        print(f"[Threads] 投稿取得エラー: {e}")
        return []


def get_notion_unposted() -> list:
    """Notion DBから「未編集」「編集済み」のエントリを取得"""
    all_pages = []
    has_more = True
    start_cursor = None

    while has_more:
        body: dict = {
            "filter": {
                "or": [
                    {
                        "property": PROP_STATUS,
                        "rich_text": {"equals": "未編集"}
                    },
                    {
                        "property": PROP_STATUS,
                        "rich_text": {"equals": "編集済み"}
                    }
                ]
            }
        }
        if start_cursor:
            body["start_cursor"] = start_cursor

        data = json.dumps(body).encode()
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
            all_pages.extend(result.get("results", []))
            has_more = result.get("has_more", False)
            start_cursor = result.get("next_cursor")
        except Exception as e:
            print(f"[Notion] DB取得エラー: {e}")
            break

    return all_pages


def extract_notion_main(page: dict) -> str:
    """Notionページの本投稿テキストを取得"""
    props = page.get("properties", {})
    items = props.get(PROP_MAIN, {}).get("rich_text", [])
    return "".join(item.get("text", {}).get("content", "") for item in items)


def update_notion_status(page_id: str, new_status: str) -> bool:
    """NotionページのステータスをPATCHで更新"""
    body = {
        "properties": {
            PROP_STATUS: {
                "rich_text": [{"type": "text", "text": {"content": new_status}}]
            }
        }
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=data,
        headers={
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        return True
    except urllib.error.HTTPError as e:
        print(f"  [Notion] PATCH エラー ({page_id[:8]}...): HTTP {e.code} {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"  [Notion] PATCH エラー ({page_id[:8]}...): {e}")
        return False


def normalize(text: str) -> str:
    """照合用に正規化（冒頭50文字・空白除去）"""
    return text.strip()[:50].replace(" ", "").replace("\n", "").replace("　", "")


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


def main() -> list:
    """
    投稿済みを検知してNotionを更新する。
    Returns: 更新したNotion page_id のリスト（フェッチャーがメトリクス取得に使用）
    """
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    print(f"[notion_mark_posted] {now_str} - 投稿済み検知スタート")

    # Threadsの最新投稿を取得
    threads_posts = get_threads_posts(limit=25)
    if not threads_posts:
        print("[notion_mark_posted] Threads投稿が取得できませんでした。")
        return []

    print(f"[notion_mark_posted] Threads投稿: {len(threads_posts)}件取得")

    # Notionの未投稿エントリを取得
    notion_pages = get_notion_unposted()
    print(f"[notion_mark_posted] Notion未投稿エントリ: {len(notion_pages)}件")

    if not notion_pages:
        print("[notion_mark_posted] 照合対象なし。")
        return []

    # Notion側を正規化してマップ化
    notion_map = {}
    for page in notion_pages:
        main_text = extract_notion_main(page)
        if main_text:
            key = normalize(main_text)
            notion_map[key] = page

    updated = []

    for post in threads_posts:
        thread_text = post.get("text", "")
        if not thread_text:
            continue

        thread_key = normalize(thread_text)

        # Notionエントリと照合
        matched_page = None
        for notion_key, page in notion_map.items():
            # 冒頭30文字が一致すれば照合成功
            if notion_key[:30] and thread_key[:30] == notion_key[:30]:
                matched_page = page
                break

        if matched_page:
            page_id = matched_page["id"]
            notion_main = extract_notion_main(matched_page)
            threads_id  = post.get("id", "")
            print(f"  [照合OK] Notion page:{page_id[:8]}... ↔ Threads:{threads_id}")

            if update_notion_status(page_id, "投稿済み"):
                print(f"  [更新OK] 「投稿済み」に変更")
                updated.append({
                    "page_id": page_id,
                    "threads_id": threads_id,
                    "text_preview": notion_main[:30],
                })
                # 使用済みのエントリを削除（重複照合防止）
                for k in list(notion_map.keys()):
                    if notion_map[k]["id"] == page_id:
                        del notion_map[k]
                        break

    if not updated:
        print("[notion_mark_posted] 新たに投稿済みになったエントリなし。")
        return []

    # Slack報告
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    lines = [
        f"✅ [自動更新] Notionステータスを「投稿済み」に更新しました（{now_str} JST）",
        f"更新件数: {len(updated)}件",
        "",
    ]
    for u in updated:
        lines.append(f"・「{u['text_preview']}…」→ 投稿済み")
    slack_notify("\n".join(lines))
    print(f"[notion_mark_posted] {len(updated)}件更新 / Slack報告完了")

    return updated


if __name__ == "__main__":
    main()
