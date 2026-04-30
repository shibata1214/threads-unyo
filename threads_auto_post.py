#!/usr/bin/env python3
"""
threads_auto_post.py
Notion DBで「編集済み」かつ予定投稿日時を過ぎているエントリを
自動でThreadsに投稿し、ステータスを「投稿済み」に更新する。

処理:
1. Notion DBから「編集済み」エントリを全取得
2. 投稿日時（タイトル列）をパースし、現在時刻（JST）を過ぎているか確認
3. 対象エントリの「本投稿」を Threads API で投稿
4. ツリー投稿がある場合は返信として投稿
5. Notion ステータスを「投稿済み」に更新
6. Slack で完了報告
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
JST  = timezone(timedelta(hours=9))

NOTION_DB_ID = "3508be18-7f31-80af-ad02-d3eb16f9452e"
PROP_TITLE   = "投稿日時"
PROP_MAIN    = "本投稿"
PROP_TREE    = "ツリー投稿"
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


# ── Notion API ───────────────────────────────────────────────

def notion_query_edited() -> list:
    """Notion DBから「編集済み」エントリを全取得"""
    all_pages = []
    has_more = True
    start_cursor = None

    while has_more:
        body: dict = {
            "filter": {
                "property": PROP_STATUS,
                "rich_text": {"equals": "編集済み"}
            }
        }
        if start_cursor:
            body["start_cursor"] = start_cursor

        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
            data=json.dumps(body).encode(),
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
            print(f"[Notion] クエリエラー: {e}")
            break

    return all_pages


def extract_title(page: dict) -> str:
    """タイトル列（投稿日時）を取得"""
    props = page.get("properties", {})
    items = props.get(PROP_TITLE, {}).get("title", [])
    return "".join(item.get("text", {}).get("content", "") for item in items)


def extract_rich_text(page: dict, prop_name: str) -> str:
    """rich_text プロパティを取得"""
    props = page.get("properties", {})
    items = props.get(prop_name, {}).get("rich_text", [])
    return "".join(item.get("text", {}).get("content", "") for item in items)


def parse_scheduled_time(title: str):
    """
    投稿日時文字列をパースしてdatetimeを返す。
    フォーマット: "YYYY-MM-DD HH:MM" or "YYYY-MM-DD 予備" (後者はNoneを返す)
    """
    title = title.strip()
    if "予備" in title or not title:
        return None
    try:
        # "YYYY-MM-DD HH:MM" をパース
        dt = datetime.strptime(title[:16], "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=JST)
    except ValueError:
        try:
            # "YYYY-MM-DD" だけの場合（時間なし）
            dt = datetime.strptime(title[:10], "%Y-%m-%d")
            return dt.replace(tzinfo=JST)
        except ValueError:
            print(f"  [警告] 投稿日時をパースできません: {title!r}")
            return None


def update_notion_status(page_id: str, new_status: str) -> bool:
    """Notion ページのステータスを更新"""
    body = {
        "properties": {
            PROP_STATUS: {
                "rich_text": [{"type": "text", "text": {"content": new_status}}]
            }
        }
    }
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=json.dumps(body).encode(),
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
    except Exception as e:
        print(f"  [Notion] ステータス更新エラー ({page_id[:8]}...): {e}")
        return False


# ── Threads API ──────────────────────────────────────────────

def threads_create_container(text: str, reply_to_id: str = None) -> str:
    """
    Threads 投稿コンテナを作成し creation_id を返す。
    失敗時は空文字を返す。
    """
    params = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN,
    }
    if reply_to_id:
        params["reply_to_id"] = reply_to_id

    data = json.dumps(params).encode()
    req = urllib.request.Request(
        f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        creation_id = result.get("id", "")
        if creation_id:
            print(f"  [Threads] コンテナ作成: {creation_id}")
        return creation_id
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"  [Threads] コンテナ作成エラー HTTP {e.code}: {body}")
        return ""
    except Exception as e:
        print(f"  [Threads] コンテナ作成エラー: {e}")
        return ""


def threads_publish(creation_id: str) -> str:
    """
    Threads コンテナを公開し thread_id を返す。
    失敗時は空文字を返す。
    """
    params = {
        "creation_id": creation_id,
        "access_token": THREADS_ACCESS_TOKEN,
    }
    data = json.dumps(params).encode()
    req = urllib.request.Request(
        f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        thread_id = result.get("id", "")
        if thread_id:
            print(f"  [Threads] 公開完了: {thread_id}")
        return thread_id
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"  [Threads] 公開エラー HTTP {e.code}: {body}")
        return ""
    except Exception as e:
        print(f"  [Threads] 公開エラー: {e}")
        return ""


def post_to_threads(main_text: str, tree_text: str = "") -> dict:
    """
    Threads に投稿する。ツリーがある場合は返信も投稿する。
    Returns: {"main_id": str, "tree_id": str}
    """
    result = {"main_id": "", "tree_id": ""}

    # メイン投稿
    print("  [Threads] メイン投稿を作成中...")
    creation_id = threads_create_container(main_text)
    if not creation_id:
        return result

    print("  [Threads] 30秒待機（Threads API要件）...")
    time.sleep(35)

    thread_id = threads_publish(creation_id)
    if not thread_id:
        return result
    result["main_id"] = thread_id

    # ツリー投稿（返信）
    if tree_text.strip():
        print("  [Threads] ツリー投稿を作成中...")
        tree_creation_id = threads_create_container(tree_text, reply_to_id=thread_id)
        if tree_creation_id:
            print("  [Threads] ツリー30秒待機...")
            time.sleep(35)
            tree_thread_id = threads_publish(tree_creation_id)
            result["tree_id"] = tree_thread_id

    return result


# ── Slack ────────────────────────────────────────────────────

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


# ── メイン ───────────────────────────────────────────────────

def main():
    now = datetime.now(JST)
    now_str = now.strftime("%Y-%m-%d %H:%M")
    print(f"[threads_auto_post] {now_str} - 自動投稿チェック開始")

    # 「編集済み」エントリを取得
    pages = notion_query_edited()
    print(f"[threads_auto_post] 「編集済み」エントリ: {len(pages)}件")

    if not pages:
        print("[threads_auto_post] 対象なし。終了。")
        return

    posted = []
    failed = []

    for page in pages:
        page_id = page["id"]
        title   = extract_title(page)
        scheduled_time = parse_scheduled_time(title)

        if scheduled_time is None:
            print(f"  [スキップ] 投稿日時なし: {title!r}")
            continue

        # 投稿予定時刻を過ぎているか確認
        if now < scheduled_time:
            remaining = int((scheduled_time - now).total_seconds() / 60)
            print(f"  [スキップ] まだ時間前: {title} (あと{remaining}分)")
            continue

        main_text = extract_rich_text(page, PROP_MAIN)
        tree_text = extract_rich_text(page, PROP_TREE)

        if not main_text.strip():
            print(f"  [スキップ] 本投稿が空: {title}")
            continue

        print(f"\n  [投稿] {title} → 「{main_text[:30]}...」")

        # Threads に投稿
        result = post_to_threads(main_text, tree_text)

        if result["main_id"]:
            # Notion ステータスを「投稿済み」に更新
            if update_notion_status(page_id, "投稿済み"):
                print(f"  [Notion] 投稿済みに更新: {page_id[:8]}...")
            posted.append({
                "title": title,
                "text_preview": main_text[:30],
                "thread_id": result["main_id"],
                "has_tree": bool(result["tree_id"]),
            })
        else:
            print(f"  [失敗] Threads投稿に失敗: {title}")
            failed.append({"title": title, "text_preview": main_text[:30]})

    # 結果報告
    if not posted and not failed:
        print("[threads_auto_post] 投稿対象なし。")
        return

    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    lines = []

    if posted:
        lines += [
            f"✅ [自動投稿] Threads投稿完了（{now_str} JST）",
            f"投稿数: {len(posted)}件",
            "",
        ]
        for p in posted:
            tree_mark = "＋ツリーあり" if p["has_tree"] else ""
            lines.append(f"・{p['title']} 「{p['text_preview']}…」 {tree_mark}")

    if failed:
        lines += [
            "",
            f"⚠️ 投稿失敗: {len(failed)}件",
        ]
        for f_ in failed:
            lines.append(f"・{f_['title']} 「{f_['text_preview']}…」")
        lines.append("→ Threadsアクセストークンの権限を確認してください。")

    slack_notify("\n".join(lines))
    print(f"[threads_auto_post] 完了: 成功{len(posted)}件 / 失敗{len(failed)}件")


if __name__ == "__main__":
    main()
