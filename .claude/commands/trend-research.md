# トレンドリサーチャー：バズり投稿収集＆ネタ反映

育児・看護師ママ・ママ系発信者のThreads投稿からバズっているものを収集し、
フック・型・内容を分析して次の投稿ネタに反映させます。

## ステップ1：バズり投稿を収集する

以下のキーワードでWebSearchを使って、Threadsでバズっている育児・ママ系投稿を収集する。
「バズっている」= いいね・リポスト・コメントが多いもの（目安：いいね50以上）

### 検索キーワード（5〜8個を使う）
- `site:threads.net 看護師ママ 育児`
- `site:threads.net 育児 バズ OR いいね`
- `site:threads.net 子ども 発熱 看護師`
- `site:threads.net ママ 育児 知らないと`
- `site:threads.net 育児 怖い OR 危ない OR 注意`
- `site:threads.net 保育園 看護師`
- `site:threads.net 子育て 意外 OR 実は OR 衝撃`
- `site:threads.net 赤ちゃん 育児 正直`

また以下のアカウントの最新投稿も確認する：
- `site:threads.net @potemama_ikuji`
- `site:threads.net @sanochan_3sai`
- `site:threads.net @tocochan_desu`
- `site:threads.net @kangoshi_mama_chan`
- `site:threads.net @hoikuen_ni_sundemasu`
- `site:threads.net @popochan_nurse`

## ステップ2：各投稿を分析する

収集した投稿ごとに以下を分析する：

```
【投稿①】
アカウント：
一文目（フック）：
フックの型：（05_writing.mdの型番号）
フックで使っている言葉カテゴリ：（禁止・逆説 / 緊迫感 / 数字 / 専門家本音 / 意外な事実 / 強い断言 / 共感・秘密 / 感情・驚き / ターゲット限定 / 権威・第三者）
内容テーマ：
バズった理由（推測）：
はるさんへの応用ネタ案：
```

## ステップ3：next-topics.md を更新する

`/Users/mina/スレッズ/next-topics.md` の末尾に以下を追記：

```
---

### トレンドリサーチ由来のネタ（YYYY-MM-DD）

#### ①（テーマ名）
- テーマ：
- 切り口：
- フック案（3つ）：
  - 「」
  - 「」
  - 「」
- 型：
- アフィリエイト：（関連する楽天商品カテゴリ）
- 優先度：高 / 中 / 低
- 参考にしたバズ投稿：（アカウント名・フック）

#### ②（テーマ名）
（同上の形式で）

#### ③（テーマ名）
（同上の形式で）

（合計5〜7件のネタを追加する）
```

## ステップ4：06_references.md を更新する

`/Users/mina/スレッズ/06_references.md` に以下を追記：

```
---

## トレンドリサーチ（YYYY-MM-DD）

### 今週バズっていた投稿・フック

| アカウント | 一文目フック | 型 | バズった理由 |
|---|---|---|---|
| （アカウント） | 「（フック）」 | 型〇〇 | （理由） |
（5〜10件追加）

### 今週のトレンドテーマ
- テーマ1：（概要）
- テーマ2：（概要）
- テーマ3：（概要）

### 使えるフック表現（新規収集）
（今回初めて見つけた強いフック表現を追加）
```

## ステップ5：GitHubにプッシュ

```bash
cd /Users/mina/スレッズ
git add next-topics.md 06_references.md
git commit -m "トレンドリサーチ更新：$(date '+%Y-%m-%d')"
git push origin main
```

## ステップ6：Notionの「リサーチストック」に保存する

Notion API（キー：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）を使って、
親ページ（ID: 3428be187f3180ff94c8fb23130319a4）の子ページとして保存する。

タイトル：「リサーチストック YYYY-MM-DD」

以下のcurlコマンドで新しいページを作成し、収集した内容を全て入れる：

```bash
TODAY=$(date '+%Y-%m-%d')

# ページ作成（本文は別途ブロックAPIで追加）
PAGE_ID=$(curl -s -X POST https://api.notion.com/v1/pages \
  -H "Authorization: Bearer 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" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent\": {\"page_id\": \"3428be187f3180ff94c8fb23130319a4\"},
    \"properties\": {
      \"title\": [{\"text\": {\"content\": \"リサーチストック $TODAY\"}}]
    }
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "作成したページID: $PAGE_ID"
```

ページ作成後、以下の内容をブロックとして追加する（`/v1/blocks/{PAGE_ID}/children` に PATCH）：

**追加する内容：**
1. 見出し「📊 今週バズっていた投稿・フック」
   - 収集した投稿を1件ずつ段落ブロックで（アカウント・フック・型・バズった理由）
2. 見出し「🔥 今週のトレンドテーマ」
   - TOP3テーマを箇条書きで
3. 見出し「💡 使えるフック表現（新規収集）」
   - 今回見つけた新しいフック表現を箇条書きで
4. 見出し「📝 next-topics.mdに追加したネタ」
   - 追加したネタのタイトルと優先度を箇条書きで

```bash
# ブロック追加（PAGE_IDは上のコマンドで取得した値を使う）
curl -s -X PATCH "https://api.notion.com/v1/blocks/$PAGE_ID/children" \
  -H "Authorization: Bearer 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" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"text":{"content":"📊 今週バズっていた投稿・フック"}}]}},
      （収集した投稿を段落ブロックで追加）,
      {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"text":{"content":"🔥 今週のトレンドテーマ"}}]}},
      （トレンドテーマを箇条書きブロックで追加）,
      {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"text":{"content":"💡 使えるフック表現（新規収集）"}}]}},
      （フック表現を箇条書きブロックで追加）,
      {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"text":{"content":"📝 next-topics.mdに追加したネタ"}}]}},
      （ネタ一覧を箇条書きブロックで追加）
    ]
  }'
```

## ステップ7：結果を報告する

```
✅ トレンドリサーチ完了！

📊 今日収集したバズり投稿：○件
🔥 今週のトレンドテーマ TOP3：
  1. 
  2. 
  3. 

📝 next-topics.mdに追加したネタ：○件
💡 特に使えそうなフック：「」
📓 Notion「リサーチストック YYYY-MM-DD」に保存しました

次の投稿生成（毎朝3時）でこのネタが反映されます。
```
