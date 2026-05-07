#!/usr/bin/env python3
"""
notion_update_metrics.py
投稿から24時間以上経過したエントリのメトリクスをThreads APIから取得し、
Notion DBの各カラム（rich_text型）に書き込む。

取得・書き込む項目: 閲覧数・ツリー閲覧数・いいね数・コメント数・リポスト数
取得不可（手動記入）: フォロー数・フォロー率

使い方: python3 notion_update_metrics.py
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
JST  = timezone(timedelta(hours=9))

NOTION_DB_ID = "3508be18-7f31-80af-ad02-d3eb16f9452e"

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


def notion_request(method: str, path: str, body: dict = None) -> dict:
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get_threads_posts(limit: int = 100) -> list:
    """Threads APIで最新投稿一覧を取得（本文・日時付き）"""
    url = (
        f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
        f"?fields=id,text,timestamp&limit={limit}"
        f"&access_token={THREADS_ACCESS_TOKEN}"
    )
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data.get("data", [])
    except Exception as e:
        print(f"[Threads] 投稿一覧取得エラー: {e}")
        return []


def get_threads_insights(post_id: str) -> dict:
    """Threads APIで投稿のインサイトを取得"""
    url = (
        f"https://graph.threads.net/v1.0/{post_id}/insights"
        f"?metric=views,likes,replies,reposts"
        f"&access_token={THREADS_ACCESS_TOKEN}"
    )
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        result = {}
        for item in data.get("data", []):
            name = item["name"]
            # total_value形式 or values形式に対応
            if "total_value" in item:
                result[name] = item["total_value"].get("value", 0)
            elif "values" in item:
                result[name] = item["values"][0].get("value", 0) if item["values"] else 0
        return result
    except Exception as e:
        print(f"  [Threads] インサイト取得エラー (post_id={post_id}): {e}")
        return {}


def get_thread_replies(post_id: str) -> list:
    """ツリー投稿（返信）のID一覧を取得"""
    url = (
        f"https://graph.threads.net/v1.0/{post_id}/replies"
        f"?fields=id,text&limit=10"
        f"&access_token={THREADS_ACCESS_TOKEN}"
    )
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data.get("data", [])
    except Exception:
        return []


def get_posted_pages_without_metrics() -> list:
    """Notion DBから「投稿済み」かつ閲覧数が空のページを取得"""
    all_pages = []
    has_more = True
    start_cursor = None

    while has_more:
        body = {
            "filter": {
                "and": [
                    {
                        "property": "ステータス（未編集／編集済み／投稿済み）",
                        "rich_text": {"equals": "投稿済み"}
                    },
                    {
                        "property": "閲覧数",
                        "rich_text": {"is_empty": True}
                    }
                ]
            }
        }
        if start_cursor:
            body["start_cursor"] = start_cursor

        result = notion_request("POST", f"/databases/{NOTION_DB_ID}/query", body)
        all_pages.extend(result.get("results", []))
        has_more = result.get("has_more", False)
        start_cursor = result.get("next_cursor")

    return all_pages


def get_prop_text(page: dict, prop_name: str) -> str:
    """rich_textプロパティの値を取得"""
    prop = page.get("properties", {}).get(prop_name, {})
    rich_text = prop.get("rich_text", [])
    if rich_text:
        return rich_text[0].get("text", {}).get("content", "")
    return ""


def get_title_text(page: dict) -> str:
    """titleプロパティ（投稿日時カラム）の値を取得"""
    prop = page.get("properties", {}).get("投稿日時", {})
    title = prop.get("title", [])
    if title:
        return title[0].get("text", {}).get("content", "")
    return ""


def parse_posted_datetime(title: str):
    """タイトル文字列から投稿日時をパース（例: '2026-05-07 19:33 面接対策'）"""
    import re
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", title)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M").replace(tzinfo=JST)
        except ValueError:
            pass
    return None


def set_rich_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": str(value)}}]}


def update_notion_metrics(page_id: str, metrics: dict) -> None:
    """Notionページの各メトリクスカラム（rich_text型）を更新"""
    properties = {}

    def add(prop_name: str, key: str):
        val = metrics.get(key)
        if val is not None:
            properties[prop_name] = set_rich_text(val)

    add("閲覧数",      "views")
    add("いいね数",    "likes")
    add("コメント数",  "replies")
    add("リポスト数",  "reposts")
    add("ツリー閲覧数", "tree_views")

    if properties:
        notion_request("PATCH", f"/pages/{page_id}", {"properties": properties})


def send_slack(message: str) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    data = json.dumps({"text": message}).encode()
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[Slack] 送信エラー: {e}")


def main():
    now = datetime.now(JST)
    print(f"[notion_update_metrics] 開始: {now.strftime('%Y-%m-%d %H:%M')} JST")

    # Notionの対象ページを取得
    pages = get_posted_pages_without_metrics()
    print(f"  メトリクス未入力の投稿済みページ: {len(pages)}件")

    if not pages:
        msg = (
            f"📊 Notionメトリクス更新（{now.strftime('%Y-%m-%d %H:%M')} JST）\n"
            "更新対象なし（全件入力済み or 投稿済みページなし）\n"
            f"Notion DB: https://www.notion.so/DB-3508be187f3180588e3eebb8681f110d"
        )
        send_slack(msg)
        print("[完了] 更新対象なし")
        return

    # Threads投稿一覧を取得（本文で照合するため）
    threads_posts = get_threads_posts(limit=100)
    print(f"  Threads投稿取得: {len(threads_posts)}件")

    # 本文先頭30文字 → {text_key: post_id} のマップを作成
    threads_map = {}
    for p in threads_posts:
        text = (p.get("text") or "").strip()
        key = text[:30]
        threads_map[key] = {
            "id": p["id"],
            "timestamp": p.get("timestamp", ""),
        }

    updated = []
    skipped_not_24h = 0
    skipped_no_match = 0

    for page in pages:
        page_id = page["id"]
        title = get_title_text(page)
        main_text = get_prop_text(page, "本投稿").strip()

        # 投稿日時チェック（24時間未満はスキップ）
        posted_at = parse_posted_datetime(title)
        if posted_at:
            hours_elapsed = (now - posted_at).total_seconds() / 3600
            if hours_elapsed < 24:
                skipped_not_24h += 1
                print(f"  スキップ（{hours_elapsed:.1f}時間経過）: {title[:35]}")
                continue

        # Threads投稿と本文で照合
        text_key = main_text[:30]
        match = threads_map.get(text_key)

        if not match:
            # 前後の空白・改行の違いを吸収して再試行
            for k, v in threads_map.items():
                if k.replace("\n", "").replace(" ", "") == text_key.replace("\n", "").replace(" ", ""):
                    match = v
                    break

        if not match:
            skipped_no_match += 1
            print(f"  スキップ（Threads投稿と照合できず）: {title[:35]}")
            continue

        threads_post_id = match["id"]
        print(f"  メトリクス取得中: {title[:35]} (Threads ID: {threads_post_id})")

        # 本投稿のインサイト取得
        metrics = get_threads_insights(threads_post_id)

        # ツリー投稿のインサイト取得
        tree_text = get_prop_text(page, "ツリー投稿").strip()
        if tree_text:
            replies = get_thread_replies(threads_post_id)
            if replies:
                tree_insights = get_threads_insights(replies[0]["id"])
                metrics["tree_views"] = tree_insights.get("views")

        # Notionを更新
        update_notion_metrics(page_id, metrics)

        updated.append({
            "title": title[:40],
            "views": metrics.get("views", 0),
            "likes": metrics.get("likes", 0),
            "replies": metrics.get("replies", 0),
            "reposts": metrics.get("reposts", 0),
            "tree_views": metrics.get("tree_views"),
        })
        v = metrics
        print(f"    → 閲覧:{v.get('views',0)} いいね:{v.get('likes',0)} コメント:{v.get('replies',0)} リポスト:{v.get('reposts',0)} ツリー閲覧:{v.get('tree_views','–')}")

    # Slack報告
    if updated:
        lines = [
            f"📊 Notionメトリクス更新完了（{now.strftime('%Y-%m-%d %H:%M')} JST）",
            f"更新件数: {len(updated)}件",
            "",
        ]
        for u in updated:
            tree_str = f" / ツリー閲覧:{u['tree_views']}" if u["tree_views"] is not None else ""
            lines.append(f"・{u['title']} | 閲覧:{u['views']} いいね:{u['likes']} コメント:{u['replies']} リポスト:{u['reposts']}{tree_str}")
        lines += [
            "",
            "※ フォロー数・フォロー率は手動記入をお願いします",
            f"Notion DB: https://www.notion.so/DB-3508be187f3180588e3eebb8681f110d",
        ]
        send_slack("\n".join(lines))
    else:
        skipped_msg = f"24時間未満:{skipped_not_24h}件 / 照合できず:{skipped_no_match}件"
        send_slack(
            f"📊 Notionメトリクス更新（{now.strftime('%Y-%m-%d %H:%M')} JST）\n"
            f"更新対象なし（{skipped_msg}）\n"
            f"Notion DB: https://www.notion.so/DB-3508be187f3180588e3eebb8681f110d"
        )

    print(f"[完了] 更新:{len(updated)}件 / 24時間未満スキップ:{skipped_not_24h}件 / 照合失敗:{skipped_no_match}件")


if __name__ == "__main__":
    main()
