#!/usr/bin/env python3
"""sitemap.xml の lastmod が指定の日より新しい住所を、IndexNow（Bing・Yandex・Naver・Seznam など）へまとめて知らせる。

    python3 scripts/seo/indexnow_ping.py                      # 送る住所の一覧を出すだけ（送らない）
    python3 scripts/seo/indexnow_ping.py --since 2026-11-20   # lastmod が 11-20 より新しい物（11-21 以降）
    python3 scripts/seo/indexnow_ping.py --apply              # 1回の POST にまとめて送り、控えに書く
    python3 scripts/seo/indexnow_ping.py --extra /llms.txt    # sitemap に無い住所を足す（同じ host の物だけ）

決まり（https://www.indexnow.org/documentation を 2026-11-23 に読んで確かめた）:
  - 鍵は 8〜128 字の英数字とダッシュ。鍵の字を中に書いた UTF-8 の `<鍵>.txt` を根に置く（根に置けば host の全住所に効く）。
  - POST の JSON は host・key・keyLocation・urlList。1回の POST で 10,000 件まで。
  - 200＝受け取った／202＝受け取ったが鍵の確かめ待ち／400 形が悪い／403 鍵が無効／422 host か鍵が合わない／429 送りすぎ。
鍵は前からある `.indexnow-key`（根の `<鍵>.txt` と同じ字・Bing が受理している物）をそのまま使う。鍵は公開する物で秘密ではない。

控え（同じ住所を1日に2度送らない・同じ lastmod の住所を2度送らない）は公開リポジトリの外に置く:
  既定 Drive `9_システム/scix-web解析/indexnow/sent.jsonl`（`SCIX_INDEXNOW_LEDGER` か --ledger で替えられる）。
  1行＝{"date": 送った日（JST）, "url", "lastmod", "status"}。200・202 の時だけ書く。
  控えの置き場の1つ上（既定は scix-web解析/）が見えないときは、送らずに止める（別の場所にフォルダを作らない）。
main への push ごとに変わった HTML は GitHub Action（.github/workflows/indexnow-on-push.yml）が scripts/ping_indexnow.py で送る。
この台本は、それとは別に sitemap の lastmod を正にして、取りこぼした住所をまとめて拾い直すためのもの。
デプロイ「後」に回す（本番にまだ無い住所を送っても意味がない）。Google は IndexNow に入っていない（sitemap と GSC が経路）。
"""
from __future__ import annotations  # launchd の python3 は 3.9＝`X | None` の注釈を実行時に評価させない

import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOST = "www.scix.co.jp"
BASE = f"https://{HOST}"
ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS = 10000
KEY_RX = re.compile(r"^[A-Za-z0-9-]{8,128}$")
JST = datetime.timezone(datetime.timedelta(hours=9))
DEFAULT_LEDGER = Path(os.environ.get(
    "SCIX_INDEXNOW_LEDGER",
    Path(os.environ.get("SCIX_WEB_LEDGER", Path.home() / "マイドライブ" / "9_システム" / "scix-web解析")) / "indexnow" / "sent.jsonl"))


def today_jst() -> str:
    return datetime.datetime.now(JST).date().isoformat()


def load_key() -> str:
    """鍵を読み、根の `<鍵>.txt` の中身と合っているかを確かめる（合わなければ止める）。"""
    key = (ROOT / ".indexnow-key").read_text(encoding="utf-8").strip()
    if not KEY_RX.match(key):
        raise SystemExit(f"鍵の形が決まり（英数字とダッシュ 8〜128 字）に合わない: {key!r}")
    kf = ROOT / f"{key}.txt"
    if not kf.is_file() or kf.read_text(encoding="utf-8").strip() != key:
        raise SystemExit(f"根に {kf.name} が無いか、中身が鍵と違う")
    return key


def sitemap_entries(path: Path) -> list[tuple[str, str]]:
    """sitemap の (loc, lastmod) を出てくる順に。lastmod の無い <url> は '' にする。"""
    xml = path.read_text(encoding="utf-8")
    out, seen = [], set()
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", block)
        if not loc or loc.group(1) in seen:
            continue
        lm = re.search(r"<lastmod>\s*(\d{4}-\d{2}-\d{2})", block)
        seen.add(loc.group(1))
        out.append((loc.group(1), lm.group(1) if lm else ""))
    return out


def read_ledger(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def pick(entries: list[tuple[str, str]], since: str, ledger: list[dict], today: str,
         extra: frozenset = frozenset()) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """送る (url, lastmod) と、外した (url, lastmod, 理由) を返す。extra の住所は --since を問わない（控えは同じに見る）。"""
    sent_today = {r.get("url") for r in ledger if r.get("date") == today}
    sent_same = {(r.get("url"), r.get("lastmod")) for r in ledger}
    send, skip = [], []
    for url, lm in entries:
        if not url.startswith(BASE + "/") and url != BASE:
            skip.append((url, lm, f"host が {HOST} でない"))
        elif url not in extra and (not lm or lm <= since):
            continue
        elif url in sent_today:
            skip.append((url, lm, "今日もう送った"))
        elif (url, lm) in sent_same:
            skip.append((url, lm, "同じ lastmod で前に送った"))
        else:
            send.append((url, lm))
    return send, skip


def post(key: str, urls: list[str]) -> int:
    body = json.dumps({"host": HOST, "key": key, "keyLocation": f"{BASE}/{key}.txt", "urlList": urls}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status
    except urllib.error.HTTPError as e:
        return e.code


MEANING = {200: "受け取った", 202: "受け取った（鍵の確かめ待ち）", 400: "形が悪い", 403: "鍵が無効（鍵ファイルが見つからない・中身が違う）",
           422: "host か鍵が合わない", 429: "送りすぎ（間を空けて送り直す）"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", help="この日（YYYY-MM-DD）より lastmod が新しい住所を送る。既定は7日前（JST）")
    ap.add_argument("--apply", action="store_true", help="本当に送る（無ければ一覧を出すだけ）")
    ap.add_argument("--extra", nargs="*", default=[], help="sitemap に無い住所を足す（/llms.txt のような根からの道・--since を問わず今日の日付で扱う）")
    ap.add_argument("--sitemap", default=str(ROOT / "sitemap.xml"), help=argparse.SUPPRESS)
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER), help="控えの置き場（既定は Drive の scix-web解析/indexnow/sent.jsonl）")
    a = ap.parse_args(argv)

    today = today_jst()
    since = a.since or (datetime.datetime.now(JST).date() - datetime.timedelta(days=7)).isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", since):
        print(f"--since は YYYY-MM-DD で: {since}", file=sys.stderr)
        return 2
    key = load_key()
    ledger_path = Path(a.ledger)
    ledger = read_ledger(ledger_path)

    entries = sitemap_entries(Path(a.sitemap))
    extra = frozenset(p if p.startswith("http") else BASE + ("" if p.startswith("/") else "/") + p for p in a.extra)
    entries += [(u, today) for u in sorted(extra)]
    send, skip = pick(entries, since, ledger, today, extra)

    print(f"sitemap {len(entries) - len(extra)} 本・lastmod が {since} より新しくて送る住所 {len(send)} 本・外した {len(skip)} 本（控え {ledger_path}）")
    ahead = sum(1 for u, lm in send if u not in extra and lm > today)
    if ahead:
        print(f"  （うち {ahead} 本は sitemap の lastmod が今日 {today} より先の日付。本番に出ている頁なら送ってよい。lastmod は公開日に合わせて直すのがよい）")
    for url, lm in send:
        print(f"  送る  {lm}  {url}")
    for url, lm, why in skip:
        print(f"  外す  {lm}  {url}  （{why}）")
    if not send:
        print("送る住所はありません。")
        return 0
    if len(send) > MAX_URLS:
        print(f"1回の POST は {MAX_URLS} 本まで（今 {len(send)} 本）。--since を新しくして分ける。", file=sys.stderr)
        return 1
    if not a.apply:
        print("\n一覧だけ（送っていない）。送るときは --apply。")
        return 0

    # 控えを書けない所（Drive が見えない端末など）で送ると、同じ住所を何度も送る元になる＝送る前に止める
    if not ledger_path.parent.is_dir() and not ledger_path.parent.parent.is_dir():
        print(f"控えの置き場 {ledger_path.parent.parent} が見えない（Drive が未マウント？）。送らずに止めた。"
              "Drive が見えている Mac で流すか、--ledger で置き場を指定する。", file=sys.stderr)
        return 2
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    status = post(key, [u for u, _ in send])
    print(f"\nHTTP {status} — {MEANING.get(status, '想定外の返事')}")
    if status not in (200, 202):
        return 1
    with ledger_path.open("a", encoding="utf-8") as f:
        for url, lm in send:
            f.write(json.dumps({"date": today, "url": url, "lastmod": lm, "status": status}, ensure_ascii=False) + "\n")
    print(f"控えに {len(send)} 行を書いた: {ledger_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
