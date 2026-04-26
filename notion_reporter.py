#!/usr/bin/env python3
"""
Notion レポーター
分析結果・運用レポートをNotionに子ページとして保存する
使い方:
  python3 notion_reporter.py analysis  "タイトル" content_file
  python3 notion_reporter.py supervisor "タイトル" content_file
"""

import sys
import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# .env からAPIキーを読み込む
env_path = Path(__file__).parent / ".env"
API_KEY = None
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("NOTION_API_KEY="):
            API_KEY = line.split("=", 1)[1].strip()

if not API_KEY:
    print("ERROR: NOTION_API_KEY が .env に見つかりません")
    sys.exit(1)

PAGE_IDS = {
    "analysis":  "3438be18-7f31-817f-95a6-cbd2d89bd6ac",   # 📊 分析レポート
    "supervisor": "3438be18-7f31-812e-b69c-f83c61e03e9c",  # 🔰 運用レポート
}

def text_to_blocks(text: str) -> list:
    """テキストをNotionブロックのリストに変換する（2000文字制限対応）"""
    blocks = []
    for line in text.splitlines():
        line = line.rstrip()

        # 見出し
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:200]}}]}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:200]}}]}})
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:200]}}]}})
        # 箇条書き
        elif line.startswith("- ") or line.startswith("* "):
            content = line[2:2000]
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": content}}]}})
        # 番号付きリスト
        elif len(line) > 2 and line[0].isdigit() and line[1] in ".、" and line[2:]:
            content = line[2:].strip()[:2000]
            blocks.append({"object": "block", "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": content}}]}})
        # 区切り線
        elif line.startswith("---") or line.startswith("==="):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        # 空行
        elif line == "":
            blocks.append({"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": []}})
        # 通常のテキスト（テーブル行はそのまま段落として）
        else:
            # 2000文字を超える行は分割
            while line:
                chunk, line = line[:2000], line[2000:]
                blocks.append({"object": "block", "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}})

    # Notion APIは一度に100ブロックまで
    return blocks[:100]

def create_page(report_type: str, title: str, content: str) -> str:
    parent_id = PAGE_IDS.get(report_type)
    if not parent_id:
        print(f"ERROR: 不明なレポートタイプ: {report_type}")
        sys.exit(1)

    blocks = text_to_blocks(content)

    payload = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": [{"text": {"content": title}}]
        },
        "children": blocks
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            page_url = result.get("url", "")
            print(f"✅ Notionに保存しました: {page_url}")
            return page_url
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"ERROR: Notion API エラー {e.code}: {error_body}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("使い方: python3 notion_reporter.py <analysis|supervisor> <タイトル> <コンテンツファイルパス>")
        sys.exit(1)

    report_type = sys.argv[1]
    title = sys.argv[2]
    content_file = sys.argv[3]

    content = Path(content_file).read_text(encoding="utf-8")
    create_page(report_type, title, content)
