# MV Hondius関連ハンタウイルス・リスク評価ダッシュボード（試行版）

GitHub Pages で動く静的ダッシュボードです。

## 今回の v2 追加点

- 疫学タイムラインを詳細化
- 症例ラインリストを追加
- Leaflet + OpenStreetMap による実地図上の航路表示
- 船の現在位置表示欄を追加
- GitHub Actions を1時間ごとに実行
- 報道ベースに加えてSNSベースの低信頼度シグナルを表示
- X/Twitterは `X_BEARER_TOKEN` が設定されている場合のみ取得
- Bluesky、Mastodon、Reddit、Google News RSSはベストエフォート取得

## GitHub Pages 公開

1. このフォルダの中身をリポジトリのルートに置く
2. GitHub の `Settings > Pages`
3. `Deploy from a branch`
4. `main / root` を選択

## 重要な設計

- WHO/ECDC等の公式情報を主データとして扱う
- 報道・SNS情報は `data/fetch_log.json` に格納し、低信頼度シグナルとして表示
- SNS情報は症例数やリスク評価を上書きしない
- 公式値が更新された場合は `data/incident.json` を手動または別スクリプトで更新する

## 任意設定

X/Twitter取得を有効にする場合は、GitHub repository secrets に以下を設定します。

- `X_BEARER_TOKEN`

## 注意

AIS/船舶位置情報サイトはCORSやスクレイピング制限があるため、取得はベストエフォートです。
正確な現在位置が必要な場合は、MarineTraffic等の正式APIまたはAISデータプロバイダのAPI利用を推奨します。
