# トレンドリサーチャー：バズり投稿収集＆ネタ反映

育児・看護師ママ・ママ系発信者のThreads＋Instagram投稿からバズっているものを収集し、
フック・型・内容を分析して次の投稿ネタに反映させます。

---

## 【Threads編】バズり投稿収集

### ステップ1：Threadsでバズり投稿を収集する

以下のキーワードでWebSearchを使って、Threadsでバズっている育児・ママ系投稿を収集する。
「バズっている」= いいね・リポスト・コメントが多いもの（目安：いいね50以上）

#### 検索キーワード（5〜8個を使う）
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

### ステップ2：Threads投稿を分析する

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

---

## 【Instagram編】バズり投稿収集

### ステップ3：Instagramでバズり投稿を収集する

`next-topics.md` と `06_references.md` を読み込んで、今週のテーマに合ったキーワードを5つ選び、
以下の形式でWebSearchを使って検索する：

#### 検索キーワード例
- `site:instagram.com 看護師ママ 育児`
- `site:instagram.com 育児ハック バズ`
- `site:instagram.com 育児便利グッズ ママ`
- `site:instagram.com 保育園準備 ママ`
- `site:instagram.com 夜泣き 対策 育児`
- `site:instagram.com 育児あるある 看護師`
- `site:instagram.com ワンオペ育児 リール`
- `site:instagram.com 乳幼児 育児 知らないと`

動画が取得できない場合は、キャプションと画像の文字情報から内容を分析する。

### ステップ4：Instagram投稿を分析する

各投稿から以下を分析する：

**フック分析（1行目の分析）：**
- どんな書き出しで始まっているか
- 数字・否定・疑問・感情ワードのどれを使っているか
- はるさんのアカウントで転用できるフック案を3つ抽出

**構成分析：**
- 投稿の型（箇条書き型・ストーリー型・断言型）
- コメント欄でよく聞かれていること（次のネタ候補）

**ジャンル別分析：**
- 医療・健康系でバズっているテーマ
- 育児グッズ・便利品でバズっているもの
- 感情共感系でバズっているテーマ

---

## ステップ5：next-topics.md を更新する

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
- 参考にしたバズ投稿：（アカウント名・フック・媒体：Threads or Instagram）

#### ②（テーマ名）
（同上の形式で）

#### ③（テーマ名）
（同上の形式で）

（合計5〜7件のネタを追加する）
```

## ステップ6：06_references.md を更新する

`/Users/mina/スレッズ/06_references.md` に以下を追記：

```
---

## トレンドリサーチ（YYYY-MM-DD）

### 今週バズっていた投稿・フック

| 媒体 | アカウント | 一文目フック | 型 | バズった理由 |
|---|---|---|---|---|
| Threads | （アカウント） | 「（フック）」 | 型〇〇 | （理由） |
| Instagram | （アカウント） | 「（フック）」 | 型〇〇 | （理由） |
（合計5〜10件追加）

### 今週のトレンドテーマ
- テーマ1：（概要）
- テーマ2：（概要）
- テーマ3：（概要）

### 使えるフック表現（新規収集）
（今回初めて見つけた強いフック表現を追加）
```

## ステップ7：GitHubにプッシュ

```bash
cd /Users/mina/スレッズ
git add next-topics.md 06_references.md
git commit -m "トレンドリサーチ更新：$(date '+%Y-%m-%d')"
git push origin main
```

## ステップ8：Notionの「リサーチストック」に保存する

Notion API（キー：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）を使って、
親ページ（ID: 3438be187f3181849c66da41c960e04d）の子ページとして保存する。

タイトル：「リサーチストック YYYY-MM-DD」

```bash
TODAY=$(date '+%Y-%m-%d')

PAGE_ID=$(curl -s -X POST https://api.notion.com/v1/pages \
  -H "Authorization: Bearer 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" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent\": {\"page_id\": \"3438be187f3181849c66da41c960e04d\"},
    \"properties\": {
      \"title\": [{\"text\": {\"content\": \"リサーチストック $TODAY\"}}]
    }
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "作成したページID: $PAGE_ID"
```

ページ作成後、以下の内容をブロックとして追加する（`/v1/blocks/{PAGE_ID}/children` に PATCH）：

**追加する内容：**
1. 見出し「📊 今週バズっていた投稿・フック（Threads＋Instagram）」
   - 収集した投稿を1件ずつ段落ブロックで（媒体・アカウント・フック・型・バズった理由）
2. 見出し「🔥 今週のトレンドテーマ」
   - TOP3テーマを箇条書きで
3. 見出し「💡 使えるフック表現（新規収集）」
   - 今回見つけた新しいフック表現を箇条書きで
4. 見出し「📝 next-topics.mdに追加したネタ」
   - 追加したネタのタイトルと優先度を箇条書きで

## ステップ9：Notionの「ネタ候補」ページを更新する

Notion API を使って、ネタ候補ページ（ID: 3438be187f31818c800dfcf77e260af8）に
ステップ5で追加したネタをブロックとして追記する。

```bash
curl -s -X PATCH "https://api.notion.com/v1/blocks/3438be187f31818c800dfcf77e260af8/children" \
  -H "Authorization: Bearer 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" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"text":{"content":"トレンドリサーチ由来のネタ（YYYY-MM-DD）"}}]}},
      （追加したネタを以下の形式で箇条書きブロックとして追加）
      {"object":"block","type":"bulleted_list_item","bulleted_list_item":{"rich_text":[{"text":{"content":"①テーマ名｜優先度：高/中/低｜フック：「」｜参考：アカウント名（Threads/Instagram）"}}]}},
      ...
    ]
  }'
```

**追加するネタのフォーマット（1件ずつ箇条書き）：**
- `①テーマ名｜優先度：高/中/低｜フック：「（フック案）」｜参考：（アカウント名・媒体）`

## ステップ10：結果を報告する

```
✅ トレンドリサーチ完了！

📊 今日収集したバズり投稿：○件（Threads：○件 / Instagram：○件）
🔥 今週のトレンドテーマ TOP3：
  1. 
  2. 
  3. 

📝 next-topics.mdに追加したネタ：○件
💡 特に使えそうなフック：「」
📓 Notion「リサーチストック YYYY-MM-DD」に保存しました

次の投稿生成（毎朝3時）でこのネタが反映されます。
```
