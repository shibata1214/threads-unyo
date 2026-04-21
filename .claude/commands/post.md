# ポスター：Threadsに投稿する

post-queue.md から「承認済み（OK）」の投稿を取り出して、Threads APIで投稿します。
ツリー投稿（自分のコメント欄への続き投稿）と楽天リンクのコメント欄投稿にも対応しています。

## 絶対ルール（必ず守ること）

1. **1回の実行で1投稿だけ。絶対に複数投稿しない。**
2. **コメント欄へのツリー投稿は1件のみ。** メイン投稿へのリプライとして1回だけ。
3. **APIエラーは1回だけリトライ。2回失敗したら即停止して報告する。**
4. **投稿成功後は必ず以下を実行する：**
   - post-queue.md から投稿済みブロックを削除
   - post-history.md に投稿記録を追記（`metrics_fetched: false`）
   - `git add post-queue.md post-history.md && git commit -m "投稿完了：YYYY-MM-DD HH:MM" && git push origin main`

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

👉 以下のどちらかで承認してください：
   ① post-queue.mdの「承認ステータス：確認待ち」を「承認ステータス：OK」に変更
   ② 「id:○○を投稿して」と直接指定
```

と報告して終了する。

4. キュー自体が空の場合：「⚠️ 投稿キューが空です。/write-post を実行してください」と報告して終了。

## ステップ2：投稿前の最終チェック

`/Users/mina/スレッズ/07_ng-rules.md` を読んで確認：
- [ ] 薬機法・医療断定表現がないか
- [ ] PR商品にPR表記があるか
- [ ] 今日の投稿数が3件未満か（post-history.mdで確認）

## ステップ3：本文を解析してメイン投稿する

**投稿前に `本文：` の中に `（以下コメント欄）` が含まれているか確認する。**

- 含まれている場合：`（以下コメント欄）` より**前の文章**だけをメイン投稿する。後の文章はステップ4でコメント欄に投稿する。`（以下コメント欄）` というテキスト自体は**どちらにも含めず削除する**。
- 含まれていない場合：本文全体をメイン投稿する。

```bash
# コンテナ作成
CONTAINER=$(curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads" \
  -H "Content-Type: application/json" \
  -d "{\"media_type\":\"TEXT\",\"text\":\"（メイン投稿本文）\",\"access_token\":\"${THREADS_ACCESS_TOKEN}\"}")

CONTAINER_ID=$(echo $CONTAINER | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")

sleep 5

# 公開
PUBLISH=$(curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads_publish" \
  -H "Content-Type: application/json" \
  -d "{\"creation_id\":\"${CONTAINER_ID}\",\"access_token\":\"${THREADS_ACCESS_TOKEN}\"}")

POST_ID=$(echo $PUBLISH | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
echo "✅ 投稿完了 POST_ID: $POST_ID"
```

## ステップ4：ツリー投稿・コメント欄への追加投稿

投稿の本文に以下のいずれかがある場合は、自分の投稿にリプライする形で追加投稿してください：

### ①本文内の（以下コメント欄）による続き投稿
`本文：` の中に `（以下コメント欄）` が含まれている場合、その**後の文章**をコメント欄に投稿する

```bash
# ツリー投稿のコンテナ作成（（以下コメント欄）より後の文章を投稿）
TREE_CONTAINER=$(curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads" \
  -H "Content-Type: application/json" \
  -d "{\"media_type\":\"TEXT\",\"text\":\"（（以下コメント欄）より後の続き文章）\",\"reply_to_id\":\"${POST_ID}\",\"access_token\":\"${THREADS_ACCESS_TOKEN}\"}")

TREE_CONTAINER_ID=$(echo $TREE_CONTAINER | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
sleep 5
curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads_publish" \
  -H "Content-Type: application/json" \
  -d "{\"creation_id\":\"${TREE_CONTAINER_ID}\",\"access_token\":\"${THREADS_ACCESS_TOKEN}\"}"
echo "✅ ツリー投稿（本文続き）完了"
```

### ②ツリー本文フィールドによる追加投稿
`ツリー投稿：あり` が指定されている場合、`ツリー本文：` の内容をコメント欄に投稿する

```bash
# ツリー投稿のコンテナ作成（reply_to_id に メイン投稿IDを指定）
TREE_CONTAINER=$(curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads" \
  -H "Content-Type: application/json" \
  -d "{\"media_type\":\"TEXT\",\"text\":\"（ツリー本文）\",\"reply_to_id\":\"${POST_ID}\",\"access_token\":\"${THREADS_ACCESS_TOKEN}\"}")

TREE_CONTAINER_ID=$(echo $TREE_CONTAINER | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")

sleep 5

# ツリー投稿を公開
curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads_publish" \
  -H "Content-Type: application/json" \
  -d "{\"creation_id\":\"${TREE_CONTAINER_ID}\",\"access_token\":\"${THREADS_ACCESS_TOKEN}\"}"
echo "✅ ツリー投稿完了"
```

### 楽天リンクをコメント欄に投稿
`楽天商品名：あり` かつ `楽天URL：（URL）` が指定されている場合：

```bash
RAKUTEN_TEXT="リンクはこちら🛍️
▶️ （楽天URL）
#PR"

RAKUTEN_CONTAINER=$(curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads" \
  -H "Content-Type: application/json" \
  -d "{\"media_type\":\"TEXT\",\"text\":\"${RAKUTEN_TEXT}\",\"reply_to_id\":\"${POST_ID}\",\"access_token\":\"${THREADS_ACCESS_TOKEN}\"}")

RAKUTEN_ID=$(echo $RAKUTEN_CONTAINER | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
sleep 5
curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID}/threads_publish" \
  -H "Content-Type: application/json" \
  -d "{\"creation_id\":\"${RAKUTEN_ID}\",\"access_token\":\"${THREADS_ACCESS_TOKEN}\"}"
echo "✅ 楽天リンクコメント投稿完了"
```

## ステップ5：投稿完了後の記録

### post-queue.md から削除
投稿した内容のブロックを削除する

### post-history.md に追記
**★ 本文は必ず全文を記録する（先頭だけはNG）**

```
---
id: （投稿のid番号）
投稿日時：（YYYY-MM-DD HH:MM）
Threads投稿ID：（POST_ID）
テーマ：（テーマ）
型：（投稿の型名）
本文（全文）：（メイン投稿の全文をそのまま貼る）
ツリー本文（全文）：（ツリー投稿がある場合、全文をそのまま貼る。なければ省略）
PR：なし or あり
楽天商品名：（商品名 or なし）
ツリー投稿：あり or なし
metrics_fetched: false
--- 数値データ（フェッチャーが追記） ---
いいね数：（未取得）
コメント数：（未取得）
リポスト数：（未取得）
引用リポスト数：（未取得）
インプレッション数：（未取得）
保存数：（未取得）
エンゲージメント率：（未取得）
---
```

### GitHubにプッシュ
```bash
cd /Users/mina/スレッズ
git add post-queue.md post-history.md
git commit -m "投稿完了：$(date '+%Y-%m-%d %H:%M')"
git push origin main
```

### Notionを更新
```bash
python3 /Users/mina/スレッズ/notion_posts_to_notion.py "$(date '+%Y-%m-%d')"
```

## ステップ6：完了報告

```
✅ 投稿完了！
テーマ：（テーマ）
投稿日時：（日時）
Threads投稿ID：（ID）
ツリー投稿：あり/なし
楽天リンクコメント：あり/なし

残りキュー：承認済み○本 / 確認待ち○本
```

**絶対ルール：1回の実行で1投稿（＋ツリー・楽天リンクは同じ投稿への返信のみ）。**

---

## 時刻指定で投稿を頼まれたとき（スケジューリングルール）

### ❌ 絶対に使わない方法
- `at` コマンド → `atd` がMacで無効なため動かない

### ✅ 必ずこの方法を使う：nohup + sleep

```bash
# 現在時刻から投稿時刻までの秒数を計算してからsleepに渡す
SECONDS_UNTIL=$(($(date -j -f "%H:%M" "HH:MM" "+%s") - $(date "+%s")))
nohup bash -c "sleep ${SECONDS_UNTIL} && bash /Users/mina/スレッズ/post_HHMM.sh > /Users/mina/スレッズ/post_HHMM.log 2>&1" &
echo "スケジュール完了 PID: $! （HH:MM に投稿）"
```

### 注意
- `nohup` を必ずつける（Claude Codeセッション終了後もプロセスが生き続ける）
- Macが常時起動・スリープなしならこれで確実に動く
- 秒数は `python3 -c` や `date` コマンドで正確に計算する
