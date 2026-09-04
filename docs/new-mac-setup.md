# scix-web 新Mac セットアップ手順

最終更新: 2026-06-21
対象: コーポレートサイト `scix-web`（静的HTML・ビルド工程なし・Vercelデプロイ）

> cockpit環境（OpenClaw / D1 / CRM / トークン類）の移行は別手順書を参照。本書は **scix-web のサイト編集を新Macで再開する**ためだけのもの。
> **要点: 中身は全部 GitHub にある。`git clone` すれば作業を再開できる。** 旧Macのディスクや専用の移行作業は基本不要。

---

## 0. 全体像（30秒）

- ソースは GitHub `nakashimashinya-a11y/scix-web` に全部ある → **clone するだけ**。
- ビルド工程なし。ローカルは簡易HTTPサーバで確認し、デプロイは Vercel。
- 必要ツールは実質4つ:
  - **git / gh** — 取得・認証
  - **node** — Vercel CLI 用
  - **python3** — ローカルプレビュー・スクリプト（`build_projects_json.py` / `ping_indexnow.py`）

---

## 1. 前提ツール

### 1-1. Xcode Command Line Tools（git・python3 が入る）
```zsh
xcode-select --install
git --version      # 確認
python3 --version  # 確認
```

### 1-2. Homebrew ＋ node（Vercel CLI 用）
```zsh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc && source ~/.zshrc
brew install node
```

### 1-3. GitHub CLI（認証＋clone が一番ラク）
```zsh
brew install gh
gh auth login   # GitHub.com → HTTPS → ブラウザ認証（アカウント: nakashimashinya-a11y）
```

---

## 2. リポジトリ取得
```zsh
mkdir -p ~/projects && cd ~/projects
gh repo clone nakashimashinya-a11y/scix-web
cd scix-web
```
gh を使わない場合:
```zsh
git clone https://github.com/nakashimashinya-a11y/scix-web.git
```

---

## 3. ローカルプレビュー（ビルド不要）
```zsh
python3 -m http.server 3847
# → ブラウザで http://localhost:3847
```
※ ポート 3847 は `.claude/launch.json` の scix-local 構成と同じ。
※ `vercel.json` の cleanUrls（.html 省略）や日本語URLリダイレクトまで再現して確認したいときは `vercel dev` を使う。

---

## 4. デプロイ（Vercel）
```zsh
npm i -g vercel
vercel login     # scix のアカウントでログイン
vercel --prod    # 本番反映
```

---

## 5. 任意: 付属スクリプト
通常のサイト編集では不要。必要なときだけ。

- **projects.json 再生成**（公開セーフな案件ティーザーを生成。nightly相当）
  ```zsh
  python3 scripts/build_projects_json.py
  ```
  → dealroom2 のデータと wrangler/D1 認証が前提。サイトの文面・HTML編集だけなら不要。
- **IndexNow 送信**（更新ページを Bing 等へ即時クロール通知）
  ```zsh
  python3 scripts/ping_indexnow.py https://www.scix.co.jp/更新したページ
  # 引数なしで sitemap.xml の全URLを送信
  ```

---

## 6. 動作確認（チェックリスト）
```zsh
git --version                  # Xcode CLT 済み
gh auth status                 # GitHub 認証済み
node -v && vercel --version    # Vercel デプロイ用
python3 --version              # プレビュー・スクリプト用
```
あとは ① clone 済み ② http://localhost:3847 が開ける ③ `vercel --prod` が通る、で復帰完了。

---

## 7. 注意点
- ビルド不要・node_modules 不要。Vercel CLI は global で入れる（`npm i -g vercel`）。
- 日本語URLや .html 省略は `vercel.json` 側のルール。ローカルで厳密に確認するなら `vercel dev`。
- GA4 測定ID（README の `G-XXXXXXXXXX`）など本番設定の置換状況は本番側で管理。秘密情報はコミットしない。
- 旧Macのディスク（SMB共有等）は scix-web の作業には不要。GitHub が正本。
