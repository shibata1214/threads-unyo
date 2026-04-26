# 楽天リサーチャー：育児系おすすめ商品調査

はるさんのアフィリエイト用に、楽天市場の育児・ママ向け人気商品と
育児系インフルエンサーが訴求しているアイテムを調査します。

## ステップ1：楽天アフィリエイトの実際の利率を確認する

楽天アフィリエイトの実際の報酬率（成果報酬）は以下のURLから確認してください：

```
https://affiliate.rakuten.co.jp/commission/
```

各カテゴリの利率を取得して、以下の参考利率（最新情報で更新）と照合してください：

| カテゴリ | 標準利率の目安 | 備考 |
|---|---|---|
| コスメ・スキンケア | 2〜5% | 高利率カテゴリ |
| ベビー・マタニティ | 2〜4% | メインジャンル |
| 食品・飲料 | 1〜4% | ポイント増量商品狙い |
| ダイエット・健康 | 2〜4% | |
| 日用品・雑貨 | 1〜3% | |
| 家電 | 0.5〜1% | 低利率・避ける |
| ファッション | 2〜4% | |

→ **利率が高い順**に商品を優先してリサーチする

## ステップ2：楽天市場でカテゴリ別人気商品を調査する

ブラウザで以下のURLにアクセスして、各カテゴリのランキングを取得してください：

### レビュー数（コメント数）が多い順
```
# ベビー・マタニティ総合ランキング
https://search.rakuten.co.jp/search/mall/育児+便利グッズ/?s=4&p=1

# 哺乳瓶・授乳グッズ
https://search.rakuten.co.jp/search/mall/哺乳瓶/?s=4

# 抱っこ紐・ベビーキャリア
https://search.rakuten.co.jp/search/mall/抱っこ紐/?s=4

# 子ども用日焼け止め
https://search.rakuten.co.jp/search/mall/子ども+日焼け止め/?s=4

# 赤ちゃん スキンケア
https://search.rakuten.co.jp/search/mall/赤ちゃん+スキンケア/?s=4

# ネッククーラー 子ども
https://search.rakuten.co.jp/search/mall/ネッククーラー+子ども/?s=4
```

※ `s=4` がレビュー数順のソート

各商品から以下を取得：
- 商品名（正式名称）
- 価格
- レビュー数・評価（★）
- 商品画像URL（楽天の商品ページから取得）
- 売れてる理由（レビューの内容から）

### 商品画像URLの取得方法
楽天商品ページで商品画像を右クリック→「画像アドレスをコピー」でURLを取得。
または、楽天商品URLの形式：`https://thumbnail.image.rakuten.co.jp/` から始まるURL

## ステップ3：育児系インフルエンサーが訴求しているアイテムを調査する

以下の方法で今トレンドの商品を把握してください：

### Instagram・Threadsで調査
ブラウザで以下を検索：
- `#楽天room 育児`
- `#楽天購入品 ベビー`
- `#ママ購入品 楽天`
- `#育児グッズ おすすめ`

バズっている投稿（いいね100以上）から：
- 何の商品を紹介しているか
- どんなフックで紹介しているか
- コメント欄での反応

### 楽天ROOMで調査
```
https://room.rakuten.co.jp/search?keyword=育児
https://room.rakuten.co.jp/search?keyword=ベビーグッズ
https://room.rakuten.co.jp/search?keyword=ママ
```

人気コレクター（フォロワー多い）が登録している商品をピックアップ

## ステップ4：結果を整理する

以下の3表を作成してください：

### 表①：利率が高い順 TOP10（メイン表）
| 順位 | 商品名 | 価格 | カテゴリ | 利率目安 | レビュー数 | 評価 | 訴求ポイント（1行） |
|---|---|---|---|---|---|---|---|

### 表②：レビュー数（コメント数）が多い順 TOP10
| 順位 | 商品名 | 価格 | レビュー数 | 評価 | カテゴリ | 利率目安 | おすすめ理由（1行） |
|---|---|---|---|---|---|---|---|

### 表③：育児系インフルエンサーが今訴求しているアイテム TOP10
| 順位 | 商品名 | 紹介しているアカウント傾向 | バズったフレーズ | 訴求ポイント |
|---|---|---|---|---|

## ステップ5：はるさん向けの投稿案を提案する

表①②③の中から「はるさんが投稿に使いやすいもの」を3つ選んで、
各商品について以下を提案してください：

```
【商品名】
カテゴリ：（カテゴリ名）
利率目安：（〇〜〇%）
訴求ポイント：（なぜこれが売れているか）
投稿フック案：（1行目の候補）
投稿の型：（どの型で紹介するか）
楽天URL：（検索URL）
商品画像URL：（画像URL）
```

## ステップ6：06_references.md に追記する

`/Users/mina/スレッズ/06_references.md` に楽天商品リストとして追記：

```
### （更新日）楽天商品リサーチ更新
【利率TOP商品】
- 商品名：価格・利率・レビュー数・訴求ポイント
（3〜5件）

【レビュー数TOP商品】
- 商品名：価格・レビュー数・訴求ポイント
（3〜5件）

【インフルエンサートレンド商品】
- 商品名：トレンド理由・フック案
（3〜5件）
```

## ステップ7：Notionの「楽天商品リサーチ」ページに保存する（画像付き）

Notion API（キー：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）を使って、
ページID `3438be18-7f31-811e-8957-daed3d4b7766`（🛍️ 楽天商品リサーチ）に
子ページとして「楽天リサーチ YYYY-MM-DD」を作成して保存してください。

子ページの内容（画像付き）：
1. **表①利率TOP10**（テーブル形式）
2. **表②レビュー数TOP10**（テーブル形式）
3. **表③インフルエンサートレンドTOP10**（テーブル形式）
4. **はるさん向け投稿案3つ**（各商品に画像＋テキスト）

### Notion APIでの画像付きページ作成

```bash
TODAY=$(date '+%Y-%m-%d')

# 子ページを作成（画像ブロックを含む）
curl -s -X POST https://api.notion.com/v1/pages \
  -H "Authorization: Bearer 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" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent\": {\"page_id\": \"3438be18-7f31-811e-8957-daed3d4b7766\"},
    \"properties\": {\"title\": [{\"text\": {\"content\": \"楽天リサーチ $TODAY\"}}]},
    \"children\": [
      {
        \"object\": \"block\",
        \"type\": \"heading_2\",
        \"heading_2\": {\"rich_text\": [{\"text\": {\"content\": \"🏆 利率TOP商品\"}}]}
      },
      （利率TOP商品の表ブロック）,
      {
        \"object\": \"block\",
        \"type\": \"heading_2\",
        \"heading_2\": {\"rich_text\": [{\"text\": {\"content\": \"⭐ レビュー数TOP商品\"}}]}
      },
      （レビュー数TOP商品の表ブロック）,
      {
        \"object\": \"block\",
        \"type\": \"heading_2\",
        \"heading_2\": {\"rich_text\": [{\"text\": {\"content\": \"📱 インフルエンサートレンド商品\"}}]}
      },
      （トレンド商品の表ブロック）,
      {
        \"object\": \"block\",
        \"type\": \"heading_2\",
        \"heading_2\": {\"rich_text\": [{\"text\": {\"content\": \"💡 はるさん向け投稿案TOP3\"}}]}
      },
      （商品1の画像ブロック）,
      {
        \"object\": \"block\",
        \"type\": \"image\",
        \"image\": {
          \"type\": \"external\",
          \"external\": {\"url\": \"（商品1の画像URL）\"}
        }
      },
      （商品1の説明テキスト）,
      （商品2の画像ブロック）,
      {
        \"object\": \"block\",
        \"type\": \"image\",
        \"image\": {
          \"type\": \"external\",
          \"external\": {\"url\": \"（商品2の画像URL）\"}
        }
      },
      （商品2の説明テキスト）,
      （商品3の画像ブロック）,
      {
        \"object\": \"block\",
        \"type\": \"image\",
        \"image\": {
          \"type\": \"external\",
          \"external\": {\"url\": \"（商品3の画像URL）\"}
        }
      },
      （商品3の説明テキスト）
    ]
  }"
```

### Notionのテーブルブロック形式

```json
{
  "object": "block",
  "type": "table",
  "table": {
    "table_width": 5,
    "has_column_header": true,
    "has_row_header": false,
    "children": [
      {
        "object": "block",
        "type": "table_row",
        "table_row": {
          "cells": [
            [{"type": "text", "text": {"content": "商品名"}}],
            [{"type": "text", "text": {"content": "価格"}}],
            [{"type": "text", "text": {"content": "利率目安"}}],
            [{"type": "text", "text": {"content": "レビュー数"}}],
            [{"type": "text", "text": {"content": "訴求ポイント"}}]
          ]
        }
      },
      （各商品の行を追加）
    ]
  }
}
```

## ステップ8：GitHubにプッシュ

```bash
cd /Users/mina/スレッズ
git add 06_references.md
git commit -m "楽天商品リサーチ更新：$(date '+%Y-%m-%d')"
git push origin main
```

## ステップ9：結果を表示する

3つの表と投稿案を日本語でわかりやすく表示してください。
「今すぐ投稿に使えるおすすめ商品TOP3（利率×レビュー数×トレンドの総合評価）」を最後に発表してください。
