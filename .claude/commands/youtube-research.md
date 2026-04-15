# YouTubeリサーチャー：自動ネタ収集

はるさんのアカウント（看護師ママ×育児×アフィリエイト）向けに、
YouTubeでバズっている動画をリサーチしてネタを収集します。

## ステップ1：検索キーワードを決める

`next-topics.md` と `06_references.md` を読み込んで、
今週のテーマに合ったYouTube検索キーワードを5つ選んでください。

はるさんのジャンルに合うキーワード例：
- 「離乳食 進め方」「夜泣き 対策」「保育園 準備」
- 「育児 看護師」「子供 発熱 対応」「ワンオペ育児」
- 「保育園洗礼」「乳幼児 風邪」「育児 便利グッズ」
- 季節・時事に合わせて追加（GW、入園、進級、夏など）

## ステップ2：ブラウザでYouTubeを検索する

各キーワードで `https://www.youtube.com/results?search_query={キーワード}` にアクセスして、
再生数が多い動画を5本ずつピックアップしてURLを取得してください。

- 再生数・投稿日・チャンネル登録者数も記録する
- 関連動画にも良いネタがあれば追加で取得する

## ステップ3：動画の文字起こしを取得する

取得した動画URLに対して、以下の方法で文字起こしを取得してください：

```bash
# youtube-transcript-api を使って文字起こし取得
pip install youtube-transcript-api 2>/dev/null || true
python3 -c "
from youtube_transcript_api import YouTubeTranscriptApi
import sys
video_id = sys.argv[1]
transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ja', 'en'])
text = ' '.join([t['text'] for t in transcript])
print(text)
" {動画ID}
```

文字起こしが取得できない場合は、動画タイトル・説明文・コメントから内容を推定してください。

## ステップ4：内容を分析する

各動画から以下を抽出・整理してください：

- 月齢・年齢ごとの具体的なやり方・スケジュール
- よくある失敗・やりがちなNG行動
- 専門家（小児科医・保健師・看護師）の見解
- 便利グッズの商品名・価格・口コミ
- ママたちが本当に悩んでいること（コメント欄から）

**フック分析（重要）：**
- 動画のタイトル（＝フック）のパターンを分析する
- バズってる動画の共通点（数字・否定・感情ワード）を特定する
- はるさんの投稿の1行目に転用できるフックを3つ抽出する

## ステップ5：06_references.md に追記する

`/Users/mina/スレッズ/06_references.md` の「投稿ネタストック」に追記：

```
### （追加日）YouTubeリサーチ追加
- 元ネタ：（YouTubeチャンネル名・動画タイトル）
- テーマ：（内容）
- 転用アイデア：（はるさんの看護師×育児視点でどう使えるか）
- 使えるフック：（具体的な1行目の案）
- 抽出した知識：（箇条書きで3〜5点）
```

## ステップ6：next-topics.md を更新する

コメント欄から拾った「ママたちが本当に悩んでいること」を
`/Users/mina/スレッズ/next-topics.md` のテーマ候補に追加してください。

## ステップ7：Notionの「リサーチストック」ページに保存する

Notion API（キー：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）を使って、
ページID `3438be18-7f31-8184-9c66-da41c960e04d`（🔍 リサーチストック）に子ページとして保存してください。

```bash
TODAY=$(date '+%Y-%m-%d')
curl -s -X POST https://api.notion.com/v1/pages \
  -H "Authorization: Bearer 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" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent\": {\"page_id\": \"3438be18-7f31-8184-9c66-da41c960e04d\"},
    \"properties\": {\"title\": [{\"text\": {\"content\": \"YouTubeリサーチ $TODAY\"}}]},
    \"children\": [（リサーチ結果・ネタ・フック案をブロックとして追加）]
  }"
```

## ステップ8：前回ログと重複チェック

`06_references.md` で既に調べた動画は重複しないようにURLを確認してください。
次回調べるべきキーワード候補も3つ提案してください。

## ステップ8：結果を表示する

- リサーチした動画数・取得ネタ数を報告
- 「今すぐ使えるフックTOP3」を表示
- 「このネタで作った投稿案」を1本だけ即興で作って見せる
