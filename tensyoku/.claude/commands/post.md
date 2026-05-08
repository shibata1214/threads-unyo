# ポスター：Threadsに投稿する

post-queue.md から「承認済み（OK）」の投稿を取り出して、Threads APIで投稿します。
1回の実行で1投稿だけ行います。

## ステップ1：投稿キューを確認する

`/Users/mina/看護師転職/post-queue.md` を読んで、以下の順で確認してください：

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

`/Users/mina/看護師転職/07_ng-rules.md` を読んで確認：
- [ ] 誹謗中傷・断定表現がないか
- [ ] PR投稿にPR表記があるか
- [ ] 投稿本文に直接URLが含まれていないか
- [ ] 今日の投稿数が3件未満か（post-history.mdで確認）

## ステップ3：Threads APIでメイン投稿する

環境変数 `THREADS_USER_ID_TENSYOKU`・`THREADS_ACCESS_TOKEN_TENSYOKU` を使用する。

```bash
# コンテナ作成
CONTAINER=$(curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID_TENSYOKU}/threads" \
  -H "Content-Type: application/json" \
  -d "{\"media_type\":\"TEXT\",\"text\":\"（投稿本文）\",\"access_token\":\"${THREADS_ACCESS_TOKEN_TENSYOKU}\"}")

CONTAINER_ID=$(echo $CONTAINER | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")

sleep 5

# 公開
PUBLISH=$(curl -s -X POST \
  "https://graph.threads.net/v1.0/${THREADS_USER_ID_TENSYOKU}/threads_publish" \
  -H "Content-Type: application/json" \
  -d "{\"creation_id\":\"${CONTAINER_ID}\",\"access_token\":\"${THREADS_ACCESS_TOKEN_TENSYOKU}\"}")

POST_ID=$(echo $PUBLISH | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
echo "✅ 投稿完了 POST_ID: $POST_ID"
```

## ステップ4：投稿完了後の記録

### post-queue.md から削除
投稿した内容のブロックを削除する

### post-history.md に追記
```
---
id: （投稿のid番号）
投稿日時：（YYYY-MM-DD HH:MM）
Threads投稿ID：（POST_ID）
テーマ：（テーマ）
型：（投稿の型名）
本文（先頭50文字）：
PR：なし or あり
エージェント名：（エージェント名 or なし）
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
cd /Users/mina/看護師転職
git add post-queue.md post-history.md
git commit -m "投稿完了：$(date '+%Y-%m-%d %H:%M')"
git push origin main
```

## ステップ5：完了報告

```
✅ 投稿完了！
テーマ：（テーマ）
投稿日時：（日時）
Threads投稿ID：（ID）

残りキュー：承認済み○本 / 確認待ち○本
```

**絶対ルール：1回の実行で1投稿のみ。**
