#!/usr/bin/env python3
"""
learn_edit.py
はるさんがNotionで編集した投稿を検出し、edit-history.md に記録する。

処理:
1. notion-originals.json を読み込み（同期時の原文）
2. 各Notionページの現在の本投稿・ツリー投稿を取得
3. 原文と比較し、変更があれば edit-history.md に追記
4. 変更パターンをまとめ、Slack報告
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
JST  = timezone(timedelta(hours=9))

ORIGINALS_FILE  = BASE / "notion-originals.json"
EDIT_HISTORY    = BASE / "edit-history.md"
WRITING_RULES   = BASE / "05_writing.md"

PROP_MAIN   = "本投稿"
PROP_TREE   = "ツリー投稿"
PROP_STATUS = "ステータス（未編集／編集済み／投稿済み）"

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

NOTION_API_KEY    = env.get("NOTION_API_KEY", "")
SLACK_WEBHOOK_URL = env.get("SLACK_WEBHOOK_URL", "")


def get_notion_page(page_id: str) -> dict:
    """NotionページのプロパティをGETで取得"""
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers={
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  [Notion] GET エラー ({page_id[:8]}...): {e}")
        return {}


def extract_rich_text(prop_data: dict) -> str:
    """rich_textプロパティから文字列を取得"""
    items = prop_data.get("rich_text", [])
    return "".join(item.get("text", {}).get("content", "") for item in items)


def extract_status(prop_data: dict) -> str:
    """ステータス（rich_text）を取得"""
    items = prop_data.get("rich_text", [])
    return "".join(item.get("text", {}).get("content", "") for item in items)


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


def load_originals() -> dict:
    if ORIGINALS_FILE.exists():
        return json.loads(ORIGINALS_FILE.read_text(encoding="utf-8"))
    return {}


def main():
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    originals = load_originals()

    if not originals:
        print("[learn_edit] notion-originals.json が空です。スキップ。")
        return

    edits = []

    print(f"[learn_edit] {len(originals)}件の投稿を確認中...")

    for post_id, data in originals.items():
        page_id = data.get("page_id", "")
        if not page_id:
            continue

        page = get_notion_page(page_id)
        if not page:
            continue

        props = page.get("properties", {})
        current_main = extract_rich_text(props.get(PROP_MAIN, {}))
        current_tree = extract_rich_text(props.get(PROP_TREE, {}))
        current_status = extract_status(props.get(PROP_STATUS, {}))

        orig_main = data.get("original_main", "")
        orig_tree = data.get("original_tree", "")

        main_changed = current_main.strip() != orig_main.strip()
        tree_changed = current_tree.strip() != orig_tree.strip()

        if main_changed or tree_changed:
            edits.append({
                "post_id": post_id,
                "status": current_status,
                "original_main": orig_main,
                "current_main": current_main,
                "original_tree": orig_tree,
                "current_tree": current_tree,
                "main_changed": main_changed,
                "tree_changed": tree_changed,
            })
            print(f"  [id:{post_id}] 編集検知 (status: {current_status})")
        else:
            print(f"  [id:{post_id}] 変更なし")

    if not edits:
        print("[learn_edit] 編集検知なし。")
        return

    # edit-history.md に追記
    history = EDIT_HISTORY.read_text(encoding="utf-8") if EDIT_HISTORY.exists() else ""

    new_entries = []
    for e in edits:
        pid = e["post_id"]
        entry_lines = [
            f"---",
            f"",
            f"## 編集記録 id:{pid}（{now_str} JST）",
            f"ステータス: {e['status']}",
            f"",
        ]
        if e["main_changed"]:
            entry_lines += [
                f"### 本投稿 Before:",
                e["original_main"],
                f"",
                f"### 本投稿 After:",
                e["current_main"],
                f"",
            ]
        if e["tree_changed"]:
            entry_lines += [
                f"### ツリー投稿 Before:",
                e["original_tree"],
                f"",
                f"### ツリー投稿 After:",
                e["current_tree"],
                f"",
            ]
        new_entries.append("\n".join(entry_lines))

    # 「## 編集記録」セクションの後ろに追記
    insert_marker = "## 編集記録\n\n（編集が発生したらここに追記される）"
    if insert_marker in history:
        new_history = history.replace(
            insert_marker,
            "## 編集記録\n\n" + "\n".join(new_entries)
        )
    else:
        new_history = history.rstrip() + "\n\n" + "\n".join(new_entries) + "\n"

    EDIT_HISTORY.write_text(new_history, encoding="utf-8")
    print(f"[learn_edit] edit-history.md に {len(edits)}件 追記しました")

    # Slack報告
    slack_lines = [
        f"✏️ [ライター] はるさんの編集を {len(edits)}件 検知しました（{now_str} JST）",
        "",
    ]
    for e in edits:
        changed = []
        if e["main_changed"]:
            changed.append("本投稿")
        if e["tree_changed"]:
            changed.append("ツリー投稿")
        slack_lines.append(f"・id:{e['post_id']}（{', '.join(changed)}を編集）")

    slack_lines += [
        "",
        "編集内容は edit-history.md に記録しました。",
        "次回の投稿生成時にはるさんの文体・傾向を反映します。",
    ]
    slack_notify("\n".join(slack_lines))
    print("[learn_edit] Slack報告完了")


if __name__ == "__main__":
    main()
