# scix.co.jp

ScienceX コーポレートサイト（静的HTML）

## ホスティング
- Vercel（推奨）またはNetlify
- カスタムドメイン: scix.co.jp

## デプロイ
```bash
npm i -g vercel
vercel --prod
```

## 構成
- `index.html` — トップページ
- `company.html` — 会社案内
- `sell.html` — 蓄電池用地の査定
- `bss.html` — 系統蓄電池事業
- `knowledge.html` — ナレッジ一覧
- `contact.html` — お問い合わせ（FormSubmit.co）
- `thanks.html` — サンクスページ
- `column-*.html` — ナレッジコラム（19本）
- `research/`（と `en/research/`）— 市場ノート。入口と月号の一覧 `/research`・速報 `/research/flash`・月号 `/research/<YYYY-MM>`・市場データ `/research/data`（2026-11-25 に `/report` から移した。古い住所は vercel.json の 308）。月号は（`scripts/build_reports.py` が Drive の `_作成物/<YYYYMM>_月報/` から焼く＝手で直さない。毎朝の同期から呼ぶ。`--check` でずれを見る。公開してはいけない語があれば書かずに止まる）
- `vercel.json` — URL設定（日本語URL→HTMLリダイレクト含む）

## SEO
- 全ページに `<title>` + `<meta name="description">` 設定済み
- iframeなし → Google完全インデックス可能
- `cleanUrls: true` → `.html` 拡張子不要

## Google Analytics
- `G-XXXXXXXXXX` をGA4の測定IDに置換してください

## DNS（お名前.com）
1. Aレコード: 76.76.21.21（Vercel）
2. CNAMEレコード: cname.vercel-dns.com
