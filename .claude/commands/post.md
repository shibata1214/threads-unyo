# ポスター：Threadsに投稿する

post-queue.md から「承認済み（OK）」の投稿を取り出して、Threads APIで投稿します。
1回の実行で1投稿だけ行います。

## ステップ1：投稿キューを確認する

`/Users/mina/スレッズ/post-queue.md` を読んで、以下の順で確認してください：

1. `承認ステータス：OK` の投稿があるか確認する
2. OKのものが複数ある場合は、**id番号が最も小さい（最も古い）もの**を選ぶ
3. OKの投稿がゼロ件の場合：

```
⚠️ 承認済みの投稿がありません。

現在のキュー状況：
- 確認待ち：○本
- 承認済み（OK）：0本

👉 Notionまたは post-queue.md を開いて、
   投稿したい投稿の「承認ステータス：確認待ち」を「承認ステータス：OK」に変更してください。
```

と報告して終了する。

4. キュー自体が空の場合：「⚠️ 投稿キューが空です。/write-post を実行して投稿を生成してください」と報告して終了。

## ステップ2：投稿前の最終チェック

`/Users/mina/スレッズ/07_ng-rules.md` を読んで、以下を確認してください：

- [ ] 薬機法・医療断定表現がないか（「治る」「効く」「治療」等の断定禁止）
- [ ] PR商品にPR表記があるか（「#PR」「（PR）」の明記）
- [ ] 差別・誹謗中傷がないか
- [ ] 文字数が適切か（200〜400文字）
- [ ] 今日の投稿数が3件未満か（`post-history.md` で今日の投稿数を確認）

今日すでに3件投稿済みの場合：
```
⚠️ 今日はすでに3件投稿しています。
凍結リスクがあるため、本日の投稿はここで終了します。
明日 9:03 の自動投稿をお待ちください。
```
と報告して終了する。

NGルール違反がある場合は投稿せず、内容と理由を報告してください。

## ステップ3：Threads APIで投稿する

環境変数 `THREADS_ACCESS_TOKEN` と `THREADS_USER_ID` を使って投稿してください。

```bash
# ステップ3-1: 投稿コンテナを作成
CONTAINER_RESPONSE=$(curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads" \
  -H "Content-Type: application/json" \
  -d "{
    \"media_type\": \"TEXT\",
    \"text\": \"（投稿本文をここに入れる・改行は\\nで表現）\",
    \"access_token\": \"${THREADS_ACCESS_TOKEN}\"
  }")

echo "Container: $CONTAINER_RESPONSE"
CONTAINER_ID=$(echo $CONTAINER_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")

# ステップ3-2: 5秒待ってから公開
sleep 5
PUBLISH_RESPONSE=$(curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads_publish" \
  -H "Content-Type: application/json" \
  -d "{
    \"creation_id\": \"${CONTAINER_ID}\",
    \"access_token\": \"${THREADS_ACCESS_TOKEN}\"
  }")

echo "Publish: $PUBLISH_RESPONSE"
POST_ID=$(echo $PUBLISH_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
echo "✅ 投稿ID: $POST_ID"
```

APIエラーが出た場合は1回だけリトライしてください。2回失敗したら投稿を中止して報告してください。

## ステップ4：投稿完了後の記録

投稿が成功したら、以下を順番に行ってください。

### 4-1: post-queue.md から削除

`/Users/mina/スレッズ/post-queue.md` から、投稿した内容のブロック（---から---まで）を削除してください。

### 4-2: post-history.md に追記

`/Users/mina/スレッズ/post-history.md` に以下フォーマットで追記：

```
---
id: （投稿のid番号）
投稿日時：（YYYY-MM-DD HH:MM）
Threads投稿ID：（APIから取得したpost_id）
テーマ：（テーマ）
型：（投稿の型名）
本文（先頭50文字）：（本文の最初50文字）
PR：なし or あり
楽天商品名：（PR投稿の場合は商品名。なし投稿は「なし」）
metrics_fetched: false
取得日時：（未取得）
--- 数値データ（フェッチャーが追記） ---
いいね数：（未取得）
コメント数：（未取得）
リポスト数：（未取得）
引用リポスト数：（未取得）
インプレッション数：（未取得）
保存数：（未取得）
エンゲージメント率：（未取得）
--- コメント分析（フェッチャーが追記） ---
注目コメント（質問）：（未取得）
注目コメント（共感）：（未取得）
---
```

### 4-3: GitHubにプッシュ

```bash
cd /Users/mina/スレッズ
git add post-queue.md post-history.md
git commit -m "投稿完了：$(date '+%Y-%m-%d %H:%M') id:（投稿ID）"
git push origin main
```

## ステップ5：完了報告

以下を報告してください：
```
✅ 投稿完了！
テーマ：（テーマ）
投稿日時：（日時）
Threads投稿ID：（ID）

残りキュー：
- 承認済み（OK）：○本
- 確認待ち：○本

次の投稿予定：（次の自動投稿時刻）
```

**絶対ルール：1回の実行で1投稿だけ。複数投稿しない。**
