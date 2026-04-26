#!/usr/bin/env python3
"""
ops-doc-updater.py
スケジュールタスクが変更されたとき、Notionの「🤖 Claude 運用ドキュメント」を自動更新する。

使い方:
  python3 ops-doc-updater.py                  # キャッシュを元にNotionを再生成
  python3 ops-doc-updater.py --from-hook      # フックから呼ばれるとき（stdinにJSON）
"""

import json
import sys
import os
from pathlib import Path
import urllib.request
import urllib.error
from datetime import datetime

# ─── 設定 ────────────────────────────────────────────────
BASE_DIR = Path("/Users/mina/スレッズ")
CACHE_FILE = BASE_DIR / "tasks-cache.json"
CONFIG_FILE = BASE_DIR / "ops-doc-config.json"
NOTION_PARENT_PAGE_ID = "3428be18-7f31-80ff-94c8-fb23130319a4"  # スレッズ投稿ストック

# .envからAPIキーを読む
NOTION_KEY = None
env_path = BASE_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("NOTION_API_KEY="):
            NOTION_KEY = line.split("=", 1)[1].strip()

if not NOTION_KEY:
    print("ERROR: NOTION_API_KEY が .env に見つかりません", file=sys.stderr)
    sys.exit(1)

# ─── Notion API ──────────────────────────────────────────
def notion_request(method, path, data=None):
    url = f"https://api.notion.com/v1{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None,
        headers={
            "Authorization": f"Bearer {NOTION_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Notion API error {e.code}: {e.read().decode()}", file=sys.stderr)
        return None

# ─── キャッシュ管理 ─────────────────────────────────────
def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}

def save_cache(tasks):
    CACHE_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def update_cache_from_hook(hook_data):
    """フックのstdinデータを元にキャッシュを更新する"""
    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})
    tool_response = hook_data.get("tool_response", {})

    cache = load_cache()

    if "create_scheduled_task" in tool_name:
        task_id = (tool_response.get("taskId") or tool_input.get("taskId", "")).strip()
        if task_id:
            cache[task_id] = {
                "taskId": task_id,
                "description": tool_input.get("description", ""),
                "schedule": tool_response.get("schedule", ""),
                "cronExpression": tool_input.get("cronExpression", ""),
                "enabled": True,
                "skill": "",
            }
            print(f"[ops-doc] タスク追加: {task_id}", file=sys.stderr)

    elif "update_scheduled_task" in tool_name:
        task_id = tool_input.get("taskId", "")
        if task_id:
            if task_id not in cache:
                cache[task_id] = {"taskId": task_id}
            for key in ["enabled", "description", "cronExpression", "schedule"]:
                if key in tool_input:
                    cache[task_id][key] = tool_input[key]
            print(f"[ops-doc] タスク更新: {task_id} enabled={tool_input.get('enabled', '?')}", file=sys.stderr)

    elif any(x in tool_name for x in ["delete", "CronDelete"]):
        task_id = tool_input.get("taskId", "")
        if task_id in cache:
            del cache[task_id]
            print(f"[ops-doc] タスク削除: {task_id}", file=sys.stderr)

    save_cache(cache)
    return cache

# ─── Notionページ管理 ────────────────────────────────────
def get_current_page_id():
    if CONFIG_FILE.exists():
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return config.get("page_id")
    return None

def save_page_id(page_id):
    CONFIG_FILE.write_text(
        json.dumps({"page_id": page_id, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")}, indent=2),
        encoding="utf-8"
    )

def archive_old_page(page_id):
    if not page_id:
        return
    result = notion_request("PATCH", f"/pages/{page_id}", {"archived": True})
    if result:
        print(f"[ops-doc] 旧ページをアーカイブ: {page_id}", file=sys.stderr)

# ─── ブロック生成ヘルパー ────────────────────────────────
def h1(text):
    return {"object": "block", "type": "heading_1",
            "heading_1": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def h2(text):
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def h3(text):
    return {"object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def p(text=""):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}] if text else []}}

def li(text):
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def num(text):
    return {"object": "block", "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def callout(text, emoji="📋", color="blue_background"):
    return {"object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": text}}],
                "icon": {"type": "emoji", "emoji": emoji},
                "color": color
            }}

def divider():
    return {"object": "block", "type": "divider", "divider": {}}

# ─── ページコンテンツ生成 ────────────────────────────────
def build_blocks(tasks, updated_at):
    enabled = {k: v for k, v in tasks.items() if v.get("enabled", False)}
    disabled = {k: v for k, v in tasks.items() if not v.get("enabled", False)}

    blocks = []

    # ヘッダー
    blocks.append(callout(
        f"Claudeがいつ・どうやって動いているかをまとめた運用ドキュメントです。スケジュールタスクが変更されると自動で更新されます。\n最終更新：{updated_at}",
        "📋", "blue_background"
    ))
    blocks.append(p())

    # 全体の流れ
    blocks.append(h1("🔄 全体の流れ"))
    blocks.append(p("リサーチ → 投稿生成 → はるさん確認・承認 → 投稿 → データ取得 → 分析 → ルール更新 → ループ"))
    blocks.append(p())

    # 自動スケジュール
    blocks.append(h1("⏰ 自動スケジュール（Claudeが勝手に動く時間）"))
    blocks.append(callout("以下はすべて「はるさんが何もしなくても自動で動く」タスクです。", "🤖", "gray_background"))
    blocks.append(p())

    # 有効タスク
    blocks.append(h2(f"✅ 稼働中（{len(enabled)}本）"))
    if enabled:
        for task_id, task in enabled.items():
            desc = task.get("description", task_id)
            schedule = task.get("schedule", "")
            skill = task.get("skill", "")
            skill_str = f" ｜ {skill}" if skill else ""
            blocks.append(h3(f"⏱ {schedule}{skill_str}"))
            blocks.append(li(desc))
            blocks.append(p())
    else:
        blocks.append(p("（現在稼働中のタスクはありません）"))
        blocks.append(p())

    # 停止中タスク
    blocks.append(h2(f"⏸ 停止中（{len(disabled)}本）"))
    if disabled:
        blocks.append(callout(
            "停止中のタスクは手動で /post などを実行することで対応しています。",
            "⚠️", "yellow_background"
        ))
        for task_id, task in disabled.items():
            desc = task.get("description", task_id)
            schedule = task.get("schedule", "")
            blocks.append(li(f"{schedule} ｜ {desc}"))
        blocks.append(p())
    else:
        blocks.append(p("（停止中のタスクはありません）"))
        blocks.append(p())

    # 手動操作
    blocks.append(h1("👋 はるさんが手動でやること"))

    blocks.append(h3("/post ｜ Threadsに1件投稿する"))
    blocks.append(num("Notion「次のテーマ候補」または post-queue.md で投稿文を確認"))
    blocks.append(num("気に入ったものの「承認ステータス：確認待ち」→「OK」に変更"))
    blocks.append(num("Claudeに「/post」と送るだけ。ツリー・楽天リンクのコメント欄投稿も自動でやってくれる"))
    blocks.append(num("1日7件まで（それ以上は凍結リスクあり）"))
    blocks.append(p())

    blocks.append(h3("/analyze ｜ 分析する（いつでもOK）"))
    blocks.append(li("フェッチャーが取得した数値をもとに勝ちパターン・負けパターンを分析"))
    blocks.append(li("analysis-latest.md・06_references.md・05_writing.md・next-topics.md に自動反映"))
    blocks.append(p())

    blocks.append(h3("/learn-edit ｜ はるさんの編集から学習する"))
    blocks.append(li("投稿文を手直ししたとき → 編集前後をClaudeに渡して実行"))
    blocks.append(li("edit-history.md と 05_writing.md を自動更新して次回の生成クオリティを上げる"))
    blocks.append(p())

    blocks.append(h3("/review ｜ 週次レビュー（週1回）"))
    blocks.append(li("今週うまくいったこと・来週の戦略をまとめてNotionに保存"))
    blocks.append(p())

    # エージェント一覧
    blocks.append(h1("🤖 エージェント一覧（6体）"))

    agents = [
        ("① リサーチャー（/trend-research）",
         "Threads＋Instagramのバズり投稿を収集してネタ・フックを抽出",
         "next-topics.md / 06_references.md / Notionリサーチストック"),
        ("② ライター（/write-post）",
         "投稿7本を自動生成。edit-history.md（はるさんの好み）を最優先参照",
         "post-queue.md / Notion「次のテーマ候補」"),
        ("③ ポスター（/post）",
         "承認済み投稿をThreads APIで実際に投稿。ツリー・楽天リンクのコメント欄投稿も担当",
         "post-history.md / post-queue.md（投稿済みを削除）"),
        ("④ フェッチャー（/fetch-metrics）",
         "投稿後24時間以上経ったものの数値をThreads APIで取得。コメントも分析",
         "post-history.md / next-topics.md / Notion「投稿実績・数値」"),
        ("⑤ アナリスト（/analyze）",
         "数値データから勝ちパターン・負けパターンを分析してルールファイルに自動反映",
         "analysis-latest.md / 06_references.md / 05_writing.md / next-topics.md / Notion「分析レポート」"),
        ("⑥ スーパーバイザー（/supervisor）",
         "運用全体の健康チェック。問題を早期発見してアラート。毎夜自動実行",
         "supervisor-report.md / Notion「運用レポート」"),
    ]
    for name, role, outputs in agents:
        blocks.append(h3(name))
        blocks.append(li(f"役割：{role}"))
        blocks.append(li(f"書き込む：{outputs}"))
        blocks.append(p())

    # 重要ファイル
    blocks.append(h1("📁 重要ファイルの役割"))
    files = [
        "edit-history.md → はるさんが手直しした投稿の傾向まとめ（ライターが最優先参照）",
        "05_writing.md → 文章ルール・フック型・投稿構成（分析・編集学習で自動更新）",
        "06_references.md → バズパターン・競合分析・トレンド・楽天商品（リサーチ・分析で自動更新）",
        "next-topics.md → 次に書くテーマ候補（リサーチ・分析・コメントから自動追記）",
        "post-queue.md → 承認待ち投稿ストック（ライターが追加→はるさんがOK→ポスターが投稿）",
        "post-history.md → 投稿記録＋数値データ（ポスター→フェッチャーの順で記録）",
        "tasks-cache.json → スケジュールタスクの状態キャッシュ（このページの自動更新に使用）",
    ]
    for f in files:
        blocks.append(li(f))
    blocks.append(p())

    # Notion連携
    blocks.append(h1("📓 Notionに自動保存されるもの"))
    notion_items = [
        "投稿案 YYYY-MM-DD → 「次のテーマ候補」ページ（毎朝ライターが生成）",
        "数値レポート YYYY-MM-DD → 「投稿実績・数値」ページ（毎夜フェッチャーが記録）",
        "分析レポート YYYY-MM-DD → 「分析レポート」ページ（アナリスト実行時）",
        "運用レポート YYYY-MM-DD → 「運用レポート」ページ（毎夜22時スーパーバイザーが記録）",
        "リサーチストック YYYY-MM-DD → 「リサーチストック」ページ（週3回リサーチャーが記録）",
    ]
    for item in notion_items:
        blocks.append(li(item))
    blocks.append(p())

    # 更新履歴（最大99ブロックまで収まるように調整済み）
    blocks.append(h1("📝 更新履歴"))
    blocks.append(callout("スケジュールタスクが変更されると自動でこのページが再生成されます。", "🔄", "green_background"))
    blocks.append(li(f"{updated_at} ｜ スケジュールタスク変更により自動更新"))

    return blocks[:99]  # Notion APIは100ブロックまで

# ─── メイン処理 ─────────────────────────────────────────
def main():
    from_hook = "--from-hook" in sys.argv

    if from_hook:
        # フックから呼ばれた場合：stdinからJSON読み込み→キャッシュ更新
        try:
            hook_data = json.load(sys.stdin)
            tasks = update_cache_from_hook(hook_data)
        except Exception as e:
            print(f"[ops-doc] stdin読み込みエラー: {e}", file=sys.stderr)
            tasks = load_cache()
    else:
        tasks = load_cache()

    if not tasks:
        print("[ops-doc] タスクキャッシュが空です", file=sys.stderr)
        return

    # 旧ページをアーカイブ
    old_page_id = get_current_page_id()
    if old_page_id:
        archive_old_page(old_page_id)

    # 新しいページを作成
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    blocks = build_blocks(tasks, updated_at)

    result = notion_request("POST", "/pages", {
        "parent": {"page_id": NOTION_PARENT_PAGE_ID},
        "properties": {
            "title": [{"text": {"content": "🤖 Claude 運用ドキュメント（いつ・どうやって動いているか）"}}]
        },
        "children": blocks
    })

    if result:
        new_page_id = result.get("id")
        new_page_url = result.get("url")
        save_page_id(new_page_id)
        print(f"[ops-doc] ✅ Notionを更新しました: {new_page_url}", file=sys.stderr)
        print(new_page_url)
    else:
        print("[ops-doc] ❌ Notionページ作成に失敗しました", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
