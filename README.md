# MV Hondius関連ハンタウイルス・リスク評価ダッシュボード（試行版） v6

## v3 修正点

- Leaflet地図の表示不具合を修正
  - `invalidateSize()` を複数回実行
  - `ResizeObserver` を追加
  - OpenStreetMap tile URLを `https://tile.openstreetmap.org/{z}/{x}/{y}.png` に変更
  - 地図コンテナの高さと幅をCSSで固定
- SNS取得を改善
  - GitHub Actions側で取得して `data/fetch_log.json` に保存
  - Bluesky / Mastodon RSS / Reddit RSS / X optional
  - Xは `X_BEARER_TOKEN` がある場合のみ取得
- 学術文献モニタリングを追加
  - PubMed E-utilities
  - 主要学術誌RSSのキーワード抽出
  - OpenAI APIキーがある場合、和訳タイトルと日本語要約を生成
- Actionsは1時間ごとに実行

## GitHub Pages

1. このフォルダの中身をリポジトリのルートに置く
2. Settings > Pages > Deploy from a branch
3. main / root を選択

## GitHub Actions

Actionsタブで `Update hantavirus incident dashboard` を手動実行できます。
毎時0分にも自動実行されます。

## Secrets

任意で以下を設定してください。

- `OPENAI_API_KEY`
  - 学術文献の和訳タイトル・日本語要約を生成
- `X_BEARER_TOKEN`
  - X/Twitter recent searchを有効化

## SNSが表示されない場合

- GitHub Actionsがまだ実行されていない可能性があります。
- Actionsタブから `workflow_dispatch` で手動実行してください。
- `data/fetch_log.json` が更新されていれば、ダッシュボードに表示されます。
- SNSは低信頼度シグナルとして表示し、公式KPIは上書きしません。

## 地図が崩れる場合

- ブラウザのキャッシュをクリアしてください。
- GitHub Pagesの反映に数分かかることがあります。
- corporate firewallでOpenStreetMap tileがブロックされる場合があります。
- 正確な船舶現在位置にはAIS商用APIの利用を推奨します。


## v4 追加修正

- 初回Actions実行前でも報道・SNSステータス・学術/専門ニュース欄が空欄にならないよう、初期seedを追加
- 「学術文献」欄を「学術・専門ニュース」欄に拡張
  - PubMed査読論文
  - 主要誌RSS
  - Scientific American / Science News / CIDRAP / Gavi / KFF / Nature / Science の専門ニュース検索
- 事例発生直後は査読論文がまだ出ていない可能性が高いため、専門ニュース・解説記事を別枠で表示
- SNS欄に取得ステータスを明示

GitHubにpushした後、必ず Actions > Update hantavirus incident dashboard > Run workflow を1回実行してください。


## v5 修正点

- 右上の日時が毎回更新されるよう、`scripts/fetch_hantavirus.py` が `data/incident.json` の `last_updated_jst` と `data_last_checked_jst` を毎回更新します。
- `fetch_log.json` の `generated_at_jst` も右上に表示します。
- ダッシュボード右上に以下を追加しました。
  - **表示を再読込**：ブラウザ上で `incident.json` と `fetch_log.json` をキャッシュバイパスして再読込
  - **GitHubで手動更新**：Actionsの `update.yml` へ移動
- GitHub Actionsは毎時0分に実行されます。
- 報道・専門ニュースの初期seedを拡充しました。
- Google News RSS、Bluesky、Mastodon RSS、Reddit RSS、任意のX API、PubMed、主要誌RSS、専門ニュース検索を取得します。

## 右上の日時が更新されない場合

1. GitHub > Actions > `Update hantavirus incident dashboard` を開く
2. 最新runが緑色で成功しているか確認
3. その後、`pages-build-deployment` が走って成功しているか確認
4. ダッシュボード右上の **表示を再読込** を押す
5. それでも古い場合はブラウザのキャッシュをクリア

## 手動アップデート

GitHub > Actions > `Update hantavirus incident dashboard` > **Run workflow** を押してください。


## v6 修正点
- WHO DON 2026-05-08（DON600）を基準にKPIとラインリストを更新。
- Actions実行時にWHO DON600相当のKPIを反映。
- 報道・SNS、ニュース・専門ニュースはハンタウイルス関連語でフィルタ。
- 報道・SNSを左、ニュース・専門ニュースを右に表示。
- 各リストは最初の20件のみ表示し、「さらに表示」で追加表示。
- ニュース・専門ニュースに和訳は付けません。
