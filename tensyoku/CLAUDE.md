# 看護師転職アカウント自動運用システム

## このプロジェクトについて
看護師ママ「みいさ」のThreads転職アフィリエイト自動運用システム。
6つのエージェントが連携して投稿生成〜投稿〜分析〜改善をループする。

## アカウントの差別化ポイント
- 病棟・夜勤ゼロで3回転職した看護師ママ
- 産婦人科クリニック → リハビリデイサービス → 整形外科クリニック
- 転職エージェント3社（ナース人材バンク・レバウェル看護・マイナビ看護師）の使用経験あり
- ターゲット：子育て中の看護師で転職を考えている人

## 重要ファイル
- `01_profile.md` : アカウント概要・コンセプト
- `02_target.md` : ターゲット像・ペルソナ
- `05_writing.md` : 文章ルール・トンマナ・フック型
- `06_references.md` : バズった投稿パターン・競合分析
- `07_ng-rules.md` : 絶対やってはいけないこと
- `next-topics.md` : 次に書くテーマ（アナリストが更新）
- `post-queue.md` : 投稿待機列（ライターが追加）
- `post-history.md` : 投稿記録
- `analysis-latest.md` : 最新分析結果

## 環境変数（別途設定が必要）
- `THREADS_USER_ID_TENSYOKU` : 転職アカウントのThreads User ID
- `THREADS_ACCESS_TOKEN_TENSYOKU` : 転職アカウントのアクセストークン
- `NOTION_API_KEY` : Notion APIキー（育児アカウントと共通でOK）
- `NOTION_TENSYOKU_POST_PAGE_ID` : 投稿案を保存するNotionページID
- `NOTION_TENSYOKU_ANALYSIS_PAGE_ID` : 分析レポートを保存するNotionページID
- `NOTION_TENSYOKU_REPORT_PAGE_ID` : 運用レポートを保存するNotionページID
- `NOTION_TENSYOKU_METRICS_PAGE_ID` : 数値データを保存するNotionページID

## 基本ルール
- 投稿文は必ず `05_writing.md` のルールに従う
- `07_ng-rules.md` の内容は絶対に違反しない
- アフィリエイトリンクには必ず「PR」を明記
- 1日3件以上の投稿は禁止（凍結リスク）
- 転職エージェントへの誘導はプロフのリンクから（Threadsに直接リンクは貼らない）
- 有益投稿：PR投稿 ＝ 7：3 の比率を守る（信頼構築を優先）
