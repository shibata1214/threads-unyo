# フェッチャー：エンゲージメントデータを全項目自動取得

投稿から24時間以上経った投稿の全数値を
Threads APIで自動取得して、post-history.md に記録します。

## ステップ1：未取得の投稿を特定する

`/Users/mina/看護師転職/post-history.md` を読んで、
`metrics_fetched: false` の投稿を全て特定してください。

- 投稿日時から24時間以上経過しているものだけを対象にする
- 24時間未満のものはスキップして次回に回す
- 対象がゼロ件の場合は「取得対象なし」と報告して終了

## ステップ2：Threads APIで全データを取得する

環境変数 `THREADS_ACCESS_TOKEN_TENSYOKU` を使って各投稿のデータを取得してください。

```bash
# ① エンゲージメント指標を取得
METRICS=$(curl -s "https://graph.threads.net/v1.0/{投稿ID}/insights?metric=likes,replies,reposts,quotes,views,saves&access_token=${THREADS_ACCESS_TOKEN_TENSYOKU}")
echo $METRICS

# ② コメント（リプライ）一覧を取得
REPLIES=$(curl -s "https://graph.threads.net/v1.0/{投稿ID}/replies?fields=text,timestamp,username&limit=50&access_token=${THREADS_ACCESS_TOKEN_TENSYOKU}")
echo $REPLIES
```

**取得する全項目：**
| 項目 | APIフィールド | 意味 |
|---|---|---|
| いいね数 | likes | リアクション数 |
| コメント数 | replies | 返信の数 |
| リポスト数 | reposts | シェアされた数 |
| 引用リポスト数 | quotes | 引用投稿された数 |
| インプレッション数 | views | 表示された回数 |
| 保存数 | saves | 保存された数（取得できれば） |

`saves` が取得できない場合はスキップしてOKです。

## ステップ3：コメントを分析する

取得したコメントを以下の基準で分類してください：

**質問コメント（★次のネタ候補★）：**
「？」「教えて」「どうしたら」「どこで」「おすすめ」「エージェント」「クリニック」「夜勤」が含まれるもの

**共感コメント（バズパターン確認）：**
「わかる」「うちも」「まさに」「ありがとう」「助かった」「同じ」が含まれるもの

**ネガティブコメント（要確認）：**
批判・否定的な内容があれば別途記録する

## ステップ4：post-history.md を更新する

`metrics_fetched: false` → `metrics_fetched: true` に更新し、取得した数値を全て記入してください：

```
metrics_fetched: true
取得日時：（YYYY-MM-DD）
--- 数値データ ---
いいね数：（数値）
コメント数：（数値）
リポスト数：（数値）
引用リポスト数：（数値）
インプレッション数：（数値）
保存数：（数値 or 取得不可）
エンゲージメント率：（（いいね+コメント+リポスト）÷ インプレッション × 100）%
--- コメント分析 ---
注目コメント（質問）：
  - （コメント本文）
注目コメント（共感）：
  - （コメント本文）
---
```

## ステップ5：next-topics.md にネタを追加する

質問コメントから次の投稿ネタを抽出して、
`/Users/mina/看護師転職/next-topics.md` に追記してください：

```
### （日付）コメントから拾ったネタ
- テーマ：（質問の内容から投稿化できるテーマ）
- 切り口：（みいさの病棟未経験・看護師ママ視点でどう使えるか）
- フック案：（1行目の案）
- 元コメント：「（実際のコメント文）」
```

## ステップ6：Notionに保存する

環境変数 NOTION_API_KEY と NOTION_TENSYOKU_METRICS_PAGE_ID を使って、
指定ページに数値データを子ページとして保存してください。

```bash
TODAY=$(date '+%Y-%m-%d')
curl -s -X POST https://api.notion.com/v1/pages \
  -H "Authorization: Bearer ${NOTION_API_KEY}" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent\": {\"page_id\": \"${NOTION_TENSYOKU_METRICS_PAGE_ID}\"},
    \"properties\": {\"title\": [{\"text\": {\"content\": \"数値レポート $TODAY\"}}]},
    \"children\": []
  }"
```

## ステップ7：GitHubにプッシュ

```bash
cd /Users/mina/看護師転職
git add post-history.md next-topics.md
git commit -m "メトリクス取得：$(date '+%Y-%m-%d') $(取得件数)件"
git push origin main
```

## ステップ8：完了報告

以下を報告してください：
- ✅ データ取得完了：（件数）件
- 📊 今週のTOP投稿：（いいね数が最多の投稿テーマ・いいね数・インプレッション数）
- 💬 コメントから拾ったネタ候補：（件数）件
- ⏳ 次回取得対象（24時間未満）：（件数）件

**注意：APIエラーが出ても止まらず、次の投稿の取得を続けること。**
