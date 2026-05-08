# MV Hondius関連ハンタウイルス・リスク評価ダッシュボード（試行版） v3

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
