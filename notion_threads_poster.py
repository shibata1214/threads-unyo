#!/usr/bin/env python3
"""
notion_threads_poster.py
Notionデータベースを監視して、指定時間にThreadsへ自動投稿するスクリプト。

【Notionデータベースのプロパティ】
  - 投稿日時: title（例: "2026-04-29 14:00"）
  - 本投稿: rich_text
  - ツリー投稿: rich_text
  - ステータス（未編集／編集済み／投稿済み）: rich_text

【処理の流れ】
1. ステータスが「編集済み」の投稿をNotion APIで取得
2. 投稿日時を解析し、現在時刻を過ぎているものを抽出
3. Threads APIで本投稿 → ツリー投稿（500文字超は自動分割）
4. Notionのステータスを「投稿済み」に更新
5. Slackに完了通知

【cronへの登録方法】
  crontab -e  で以下を追加:
  */13 * * * * /usr/bin/python3 /Users/mina/看護師転職スレッズ運用/notion_threads_poster.py >> /Users/mina/看護師転職スレッズ運用/poster.log 2>&1
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Tuple, List

# ── 設定 ────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent
NOTION_DB_ID = "3508be18-7f31-80af-ad02-d3eb16f9452e"
JST = timezone(timedelta(hours=9))
THREADS_MAX_CHARS = 500

# Notionプロパティ名（実際のDB列名に合わせる）
PROP_TITLE    = "投稿日時"
PROP_MAIN     = "本投稿"
PROP_TREE     = "ツリー投稿"
PROP_STATUS   = "ステータス（未編集／編集済み／投稿済み）"
STATUS_READY  = "編集済み"
STATUS_POSTED = "投稿済み"

# 対応する日時フォーマット（入力例を想定して複数対応）
DATE_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
]

# .env 読み込み
env: dict = {}
env_path = BASE / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        env[key.strip()] = val.strip()

NOTION_API_KEY       = env.get("NOTION_API_KEY", "")
THREADS_USER_ID      = env.get("THREADS_USER_ID", "")
THREADS_ACCESS_TOKEN = env.get("THREADS_ACCESS_TOKEN", "")
SLACK_WEBHOOK_URL    = env.get("SLACK_WEBHOOK_URL", "")


# ── ユーティリティ ───────────────────────────────────────────

def parse_datetime(date_str: str) -> Optional[datetime]:
    """日時文字列をJST datetimeに変換。失敗時はNoneを返す。
    時間が1桁（例: 6:32）でも自動補完して認識する。
    """
    import re
    date_str = date_str.strip()
    # 「2026-05-05 6:32」→「2026-05-05 06:32」のようにゼロ補完
    date_str = re.sub(r'(\s)(\d):', r'\g<1>0\2:', date_str)
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=JST)
        except ValueError:
            continue
    return None


def split_tree_text(text: str) -> List[str]:
    """
    ツリー投稿テキストを500文字以内のチャンクに分割する。
    段落（空行）区切りを優先し、それでも超える場合は改行で分割する。
    """
    if len(text) <= THREADS_MAX_CHARS:
        return [text]

    chunks: List[str] = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= THREADS_MAX_CHARS:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # 段落自体が500文字を超える場合は改行で分割
            if len(para) > THREADS_MAX_CHARS:
                lines = para.split("\n")
                current = ""
                for line in lines:
                    candidate = (current + "\n" + line).strip() if current else line
                    if len(candidate) <= THREADS_MAX_CHARS:
                        current = candidate
                    else:
                        if current:
                            chunks.append(current)
                        current = line
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


# ── Notion API ───────────────────────────────────────────────

def notion_req(method: str, path: str, payload: Optional[dict] = None):
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(payload, ensure_ascii=False).encode() if payload else None
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:400]
        print(f"  [Notion API] HTTP {e.code}: {body}")
        return None
    except Exception as e:
        print(f"  [Notion API] エラー: {e}")
        return None


def get_text(page: dict, prop_name: str) -> str:
    """Notionページのrich_text / title プロパティをプレーンテキストで取得"""
    prop = page.get("properties", {}).get(prop_name, {})
    ptype = prop.get("type", "")
    if ptype == "rich_text":
        return "".join(rt.get("plain_text", "") for rt in prop.get("rich_text", []))
    if ptype == "title":
        return "".join(rt.get("plain_text", "") for rt in prop.get("title", []))
    return ""


def get_pending_posts() -> List[dict]:
    """
    ステータスが「編集済み」かつ投稿日時が現在時刻以前の投稿を取得。
    投稿日時はtitle型のため、Notion側ではステータスのみフィルタし、
    日付の比較はPython側で実施する。
    """
    now = datetime.now(JST)
    payload = {
        "filter": {
            "property": PROP_STATUS,
            "rich_text": {"equals": STATUS_READY},
        },
        "page_size": 100,
    }
    result = notion_req("POST", f"/databases/{NOTION_DB_ID}/query", payload)
    if not result:
        return []

    pending = []
    for page in result.get("results", []):
        date_str = get_text(page, PROP_TITLE)
        if not date_str:
            print(f"  ⚠️ 投稿日時が空のエントリをスキップ (page_id: {page['id']})")
            continue
        scheduled = parse_datetime(date_str)
        if scheduled is None:
            print(f"  ⚠️ 日時解析失敗: '{date_str}' — スキップ")
            continue
        if scheduled <= now:
            pending.append(page)
        else:
            diff = scheduled - now
            h, m = divmod(int(diff.total_seconds()) // 60, 60)
            print(f"  まだ時間前: [{date_str}] あと{h}時間{m}分")

    # 投稿日時の昇順にソート
    def sort_key(p):
        return parse_datetime(get_text(p, PROP_TITLE)) or now

    pending.sort(key=sort_key)
    return pending


def update_status(page_id: str) -> bool:
    """Notionのステータスを「投稿済み」に更新"""
    result = notion_req(
        "PATCH", f"/pages/{page_id}",
        {
            "properties": {
                PROP_STATUS: {
                    "rich_text": [{"type": "text", "text": {"content": STATUS_POSTED}}]
                }
            }
        },
    )
    return result is not None


# ── Threads API ──────────────────────────────────────────────

def threads_create_container(text: str, reply_to_id: Optional[str] = None) -> Optional[str]:
    """投稿コンテナを作成し、container_idを返す"""
    payload: dict = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN,
    }
    if reply_to_id:
        payload["reply_to_id"] = reply_to_id

    url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read())
            return res.get("id")
    except urllib.error.HTTPError as e:
        print(f"  [Threads] コンテナ作成 HTTP {e.code}: {e.read().decode()[:300]}")
        return None
    except Exception as e:
        print(f"  [Threads] コンテナ作成エラー: {e}")
        return None


def threads_publish(container_id: str) -> Optional[str]:
    """コンテナを公開し、post_idを返す"""
    url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    payload = {"creation_id": container_id, "access_token": THREADS_ACCESS_TOKEN}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read())
            return res.get("id")
    except urllib.error.HTTPError as e:
        print(f"  [Threads] 公開 HTTP {e.code}: {e.read().decode()[:300]}")
        return None
    except Exception as e:
        print(f"  [Threads] 公開エラー: {e}")
        return None


def post_to_threads(main_text: str, tree_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Threadsへメイン投稿＋ツリー投稿を行う。
    ツリーが500文字超の場合は複数の連鎖投稿に分割する。
    戻り値: (post_id, last_tree_post_id)  失敗時はNone。
    """

    # ── メイン投稿 ──
    print("  📤 メイン投稿コンテナ作成中...")
    container_id = threads_create_container(main_text)
    if not container_id:
        print("  ❌ メイン投稿コンテナ作成失敗")
        return None, None

    time.sleep(5)

    print("  📤 メイン投稿公開中...")
    post_id = threads_publish(container_id)
    if not post_id:
        print("  ❌ メイン投稿公開失敗")
        return None, None

    print(f"  ✅ メイン投稿完了 POST_ID: {post_id}")

    # ── ツリー投稿（テキストがある場合のみ）──
    tree_post_id = None
    if tree_text and tree_text.strip():
        chunks = split_tree_text(tree_text.strip())
        print(f"  ツリー投稿: {len(chunks)}チャンクに分割")

        reply_to = post_id
        for i, chunk in enumerate(chunks):
            time.sleep(3)
            print(f"  📤 ツリー投稿[{i+1}/{len(chunks)}] コンテナ作成中... ({len(chunk)}文字)")
            tree_container_id = threads_create_container(chunk, reply_to_id=reply_to)
            if not tree_container_id:
                print(f"  ❌ ツリーコンテナ作成失敗（チャンク{i+1}）")
                return post_id, tree_post_id

            time.sleep(5)
            print(f"  📤 ツリー投稿[{i+1}/{len(chunks)}] 公開中...")
            chunk_post_id = threads_publish(tree_container_id)
            if chunk_post_id:
                print(f"  ✅ ツリー投稿[{i+1}] 完了 ID: {chunk_post_id}")
                tree_post_id = chunk_post_id
                reply_to = chunk_post_id
            else:
                print(f"  ❌ ツリー投稿[{i+1}] 公開失敗")
                return post_id, tree_post_id

    return post_id, tree_post_id


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
    except Exception as e:
        print(f"  [Slack] 通知エラー: {e}")


# ── メイン ───────────────────────────────────────────────────

def main() -> None:
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*52}")
    print(f"Notion→Threads 自動投稿チェック: {now_str}")
    print(f"{'='*52}")

    if not NOTION_API_KEY:
        print("ERROR: NOTION_API_KEY が .env に設定されていません")
        return
    if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
        print("ERROR: THREADS の認証情報が .env に設定されていません")
        return

    posts = get_pending_posts()
    print(f"投稿対象: {len(posts)}件")

    if not posts:
        print("投稿対象なし。終了。")
        return

    success_count = 0
    fail_count = 0

    for page in posts:
        page_id    = page["id"]
        main_text  = get_text(page, PROP_MAIN)
        tree_text  = get_text(page, PROP_TREE)
        date_str   = get_text(page, PROP_TITLE)

        print(f"\n--- 処理中: [{date_str}] ---")
        print(f"  本投稿: {main_text[:50]}{'...' if len(main_text) > 50 else ''}")
        if tree_text:
            print(f"  ツリー: {tree_text[:40]}{'...' if len(tree_text) > 40 else ''}")

        if not main_text.strip():
            print("  ❌ 本投稿テキストが空のためスキップ")
            continue

        post_id, tree_post_id = post_to_threads(main_text, tree_text)

        if post_id:
            if update_status(page_id):
                print("  ✅ Notionステータス → 投稿済み")
            else:
                print("  ⚠️ Notionステータス更新失敗（要手動確認）")

            has_tree = bool(tree_text and tree_text.strip())
            if has_tree and not tree_post_id:
                print("  ⚠️ ツリー投稿が失敗しました（要手動確認）")
                slack_notify(
                    f"⚠️ 本投稿は成功しましたが、ツリー投稿が失敗しました。\n"
                    f"投稿日時: {date_str}\n"
                    f"本投稿ID: {post_id}\n"
                    f"手動でツリーを投稿してください。"
                )
            else:
                msg_lines = [
                    "✅ 自動投稿が完了しました。",
                    f"投稿日時: {date_str}",
                    f"本投稿ID: {post_id}",
                ]
                if tree_post_id:
                    msg_lines.append(f"ツリー投稿ID: {tree_post_id}")
                slack_notify("\n".join(msg_lines))
            success_count += 1
        else:
            print("  ❌ 投稿失敗")
            slack_notify(
                f"⚠️ Threads投稿に失敗しました。\n"
                f"投稿日時: {date_str}\n"
                f"本文（先頭）: {main_text[:60]}..."
            )
            fail_count += 1

    print(f"\n{'='*52}")
    print(f"完了: 成功 {success_count}件 / 失敗 {fail_count}件")
    print(f"{'='*52}\n")


if __name__ == "__main__":
    main()
