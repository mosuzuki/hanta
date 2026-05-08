# MV Hondius関連ハンタウイルス・リスク評価ダッシュボード（試行版）

GitHub Pages で動作する静的ダッシュボードです。WHO Disease Outbreak News、ECDC assessment / press release、報道・専門ニュースの補助シグナルを分けて表示します。

## 目的

このダッシュボードは、MV Hondius関連ハンタウイルス事案について、リスク評価に必要な情報を整理するための **incident dashboard** です。一般的なハンタウイルス監視ではなく、以下に特化しています。

- 症例・死亡・重症例の公式値
- 発症・下船・医療搬送・公式通知のタイムライン
- 船内・下船者・受入国一般市民・EU/EEA一般人口へのリスク評価
- 感染経路仮説の整理
- 接触者追跡と運用状況
- 公式情報と報道シグナルの分離

## ファイル構成

```text
.
├── index.html
├── style.css
├── app.js
├── data/
│   ├── incident.json
│   └── sources.json
├── scripts/
│   └── fetch_hantavirus.py
└── .github/workflows/
    └── update.yml
```

## GitHub Pages で公開する方法

1. このフォルダの中身を GitHub リポジトリのルートに置く。
2. GitHub の **Settings → Pages** を開く。
3. **Build and deployment** で `Deploy from a branch` を選ぶ。
4. Branch は `main`、folder は `/ (root)` を指定する。
5. 数分後に GitHub Pages の URL で公開されます。

## データ更新

`data/incident.json` を編集すると画面が更新されます。

GitHub Actions による自動更新も用意しています。

- `.github/workflows/update.yml` は毎日 08:00 JST 前後に実行されます。
- `scripts/fetch_hantavirus.py` は公式・補助ソースを取得し、現在は安全のため **公式値の手動確認を前提にした半自動更新** としています。
- 完全自動の数値上書きは、公式値と報道値の矛盾がある場合に危険なので、初期版では避けています。

## OpenAI API によるAIサマリー生成を追加する場合

GitHub repository secrets に `OPENAI_API_KEY` を追加し、`scripts/fetch_hantavirus.py` 内の `USE_OPENAI_SUMMARY = False` を `True` に変更してください。

ただし、リスク評価では、AIは独自判断ではなく以下に限定することを推奨します。

- 差分抽出
- 新旧の症例数比較
- 公式情報と報道情報の矛盾検出
- 不確実性と注視点の整理

## 注意

このダッシュボードは公衆衛生上の意思決定を直接代替するものではありません。公式発表、IHR連絡、各国当局の情報を優先してください。
