#!/usr/bin/env python3
"""scix.co.jp の検索・行動データ収集と週次自動更新の共通部品（標準ライブラリのみ）。

台帳（データの置き場）は Drive `9_システム/scix-web解析/`。公開リポジトリには数字を置かない。
  gsc/YYYY-MM-DD.json     Search Console の日次（検索語×ページ・ページ・端末・国）
  ga4/YYYY-MM-DD.json     GA4 の日次（着地・ページ・内部遷移・イベント・チャネル）
  health/YYYY-MM-DD.json  本番HTMLの健診（status・title・description・canonical・内部リンク）
  ledger/changes.jsonl    自動更新と手動PRの変更台帳（効果測定の対象）
  ledger/measurements.jsonl 変更の2週後・4週後の前後比較
  weekly/YYYY-MM-DD/      週次のブリーフ・変更マニフェスト・結果

Google の認証はコックピットと同じ `~/.config/scix-cockpit/` のトークンを使う。
  sc_token.json   Search Console（webmasters.readonly）
  ga4_token.json  GA4 Data API（analytics.readonly）— 無ければ `python3 scripts/seo/ga4_auth.py` で1回だけ取得
"""
from __future__ import annotations  # launchd の python3 は 3.9＝`X | None` の注釈を実行時に評価させない
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOME = pathlib.Path.home()
REPO = pathlib.Path(os.environ.get("SCIX_WEB_REPO", HOME / "projects" / "scix-web"))
LEDGER = pathlib.Path(os.environ.get("SCIX_WEB_LEDGER", HOME / "マイドライブ" / "9_システム" / "scix-web解析"))
CFG = HOME / ".config" / "scix-cockpit"
SC_TOKEN = CFG / "sc_token.json"
GA4_TOKEN = CFG / "ga4_token.json"
GSC_SITE = "sc-domain:scix.co.jp"
GA4_PROPERTY = "532483329"
HOST = "www.scix.co.jp"
BASE = f"https://{HOST}"
def _tg_target() -> str:
    """宛先はリポジトリの外から取る（公開リポジトリに個人の宛先を書かない）。"""
    v = os.environ.get("SCIX_TG_TARGET")
    if v:
        return v.strip()
    try:
        with open(os.path.expanduser("~/.config/scix-web/tg_target"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


TG_TARGET = _tg_target()
UA = "scix-web-metrics/1.0 (+https://www.scix.co.jp/company)"

# 収益ページ（問い合わせに直結する着地・遷移先）。優先順位は 買い手 ≧ 投資家 ＞ 土地。
COMMERCIAL = ["/projects", "/transfer", "/investors", "/fund", "/sourcing", "/land",
              "/contact", "/sell-form", "/en/contact", "/zh-contact"]


def log(msg: str) -> None:
    print(time.strftime("%F %T"), msg, flush=True)


def today() -> datetime.date:
    return datetime.date.today()


def d(s: str) -> datetime.date:
    return datetime.date.fromisoformat(s)


def safe_d(s):
    """d() と同じ。ただし暦に無い日付（"2026-09-31"）・空・文字列でないものは None（落とさない）。"""
    try:
        return datetime.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def daterange(start: datetime.date, end: datetime.date):
    cur = start
    while cur <= end:
        yield cur
        cur += datetime.timedelta(days=1)


def jload(path: pathlib.Path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        log(f"壊れたJSON {path}: {e}")
        return default


def jdump(path: pathlib.Path, obj) -> None:
    """途中で落ちても半端なファイルを残さない（tmp→rename）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=None, separators=(",", ":"))
    os.replace(tmp, path)


def append_jsonl(path: pathlib.Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path: pathlib.Path):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except FileNotFoundError:
        pass
    return out


def write_jsonl(path: pathlib.Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- Google API

class Google:
    """refresh_token でアクセストークンを更新して JSON API を叩く。googleapiclient に依存しない
    （launchd から動く python3 にはライブラリが入っていない。2026-09-19 実測）。"""

    def __init__(self, token_path: pathlib.Path):
        self.path = token_path
        self.t = jload(token_path)
        if not self.t:
            raise FileNotFoundError(f"トークンが無い: {token_path}")
        self.access = None
        self.exp = 0.0

    def token(self) -> str:
        if self.access and time.time() < self.exp - 60:
            return self.access
        t = self.t
        data = urllib.parse.urlencode({
            "client_id": t["client_id"], "client_secret": t["client_secret"],
            "refresh_token": t["refresh_token"], "grant_type": "refresh_token",
        }).encode()
        req = urllib.request.Request(t.get("token_uri", "https://oauth2.googleapis.com/token"), data=data)
        with urllib.request.urlopen(req, timeout=30) as res:
            j = json.load(res)
        self.access = j["access_token"]
        self.exp = time.time() + int(j.get("expires_in", 3600))
        return self.access

    def call(self, url: str, body=None, retries: int = 4):
        payload = json.dumps(body).encode() if body is not None else None
        last = None
        for attempt in range(retries):
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": "Bearer " + self.token(),
                "Content-Type": "application/json",
                "User-Agent": UA,
            })
            try:
                with urllib.request.urlopen(req, timeout=120) as res:
                    return json.load(res)
            except urllib.error.HTTPError as e:
                text = e.read().decode("utf-8", "replace")[:300]
                last = f"HTTP {e.code}: {text}"
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** attempt * 3)
                    continue
                raise RuntimeError(last) from None
            except (urllib.error.URLError, TimeoutError) as e:
                last = str(e)
                time.sleep(2 ** attempt * 3)
        raise RuntimeError(f"Google API が応答しない: {last}")


def gsc_query(g: Google, start, end, dims, row_limit=25000, dim_filters=None, data_state=None):
    """searchAnalytics.query。25,000行を超えたら startRow で続きを取る。"""
    site = urllib.parse.quote(GSC_SITE, safe="")
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
    rows, start_row = [], 0
    while True:
        body = {"startDate": str(start), "endDate": str(end), "dimensions": dims,
                "rowLimit": row_limit, "startRow": start_row}
        if dim_filters:
            body["dimensionFilterGroups"] = [{"filters": dim_filters}]
        if data_state:
            body["dataState"] = data_state
        r = g.call(url, body)
        got = r.get("rows", [])
        rows.extend(got)
        if len(got) < row_limit:
            break
        start_row += row_limit
    return rows


def ga4_report(g: Google, start, end, dims, mets, dim_filter=None, limit=100000, order_by=None):
    """GA4 Data API runReport。dims/mets は API 名。行は {dim名: 値, met名: 数値} の dict で返す。"""
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4_PROPERTY}:runReport"
    out, offset = [], 0
    while True:
        body = {
            "dateRanges": [{"startDate": str(start), "endDate": str(end)}],
            "dimensions": [{"name": x} for x in dims],
            "metrics": [{"name": x} for x in mets],
            "limit": limit, "offset": offset,
            "keepEmptyRows": False,
        }
        if dim_filter:
            body["dimensionFilter"] = dim_filter
        if order_by:
            body["orderBys"] = order_by
        r = g.call(url, body)
        dh = [x["name"] for x in r.get("dimensionHeaders", [])]
        mh = [x["name"] for x in r.get("metricHeaders", [])]
        for row in r.get("rows", []):
            rec = {}
            for k, v in zip(dh, row.get("dimensionValues", [])):
                rec[k] = v.get("value")
            for k, v in zip(mh, row.get("metricValues", [])):
                val = v.get("value")
                try:
                    rec[k] = float(val) if "." in str(val) else int(val)
                except (TypeError, ValueError):
                    rec[k] = val
            out.append(rec)
        total = int(r.get("rowCount", 0))
        offset += limit
        if offset >= total or not r.get("rows"):
            break
    return out


# ---------------------------------------------------------------- 通知

def tg_send(msg: str) -> bool:
    """Telegram（中島さん宛）。rc を必ず見る。--target/--message が正しいフラグ（--to/--text は無い）。"""
    if not TG_TARGET:
        log("Telegram 宛先が未設定（SCIX_TG_TARGET）。送らずに続ける: %s" % msg[:80])
        return False
    try:
        r = subprocess.run(["openclaw", "message", "send", "--channel", "telegram",
                            "--target", TG_TARGET, "--message", msg],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            log("Telegram 送信失敗 rc=%d %s" % (r.returncode, (r.stderr or r.stdout)[:200]))
            return False
        return True
    except Exception as e:  # noqa: BLE001
        log("Telegram 送信失敗: %s" % e)
        return False


# ---------------------------------------------------------------- URL/ファイル

def url_to_file(url: str) -> pathlib.Path | None:
    path = url[len(BASE):] if url.startswith(BASE) else url
    path = path.split("?")[0].split("#")[0] or "/"
    if path == "/":
        return REPO / "index.html"
    if path == "/en":
        return REPO / "en" / "index.html"
    cand = REPO / (path.lstrip("/") + ".html")
    return cand if cand.exists() else None


def file_to_url(rel: str) -> str | None:
    if not rel.endswith(".html") or rel == "404.html":
        return None
    slug = rel[:-5]
    if slug == "index":
        return BASE + "/"
    if slug == "en/index":
        return BASE + "/en"
    return f"{BASE}/{slug}"


def path_of(url: str) -> str:
    """https://www.scix.co.jp/foo?x → /foo"""
    p = url[len(BASE):] if url.startswith(BASE) else url
    p = p.split("?")[0].split("#")[0]
    return p or "/"
