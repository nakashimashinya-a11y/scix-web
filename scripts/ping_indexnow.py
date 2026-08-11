#!/usr/bin/env python3
"""Tell IndexNow (Bing / Yandex / Naver など) which URLs changed.

Google は IndexNow に参加していないので、Google 側は Search Console の
「URL検査 → インデックス登録をリクエスト」が必要。これはその他の検索エンジン用。

    python3 scripts/ping_indexnow.py --changed-since main   # ブランチの差分から自動で拾う
    python3 scripts/ping_indexnow.py /qa /grid-storage      # URLを直接指定
    python3 scripts/ping_indexnow.py --sitemap              # sitemap の全URL（初回のみ推奨）

デプロイ「後」に実行すること。まだ本番に出ていないURLを送っても意味がない。
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

HOST = "www.scix.co.jp"
BASE = f"https://{HOST}"
KEY = Path(".indexnow-key").read_text(encoding="utf-8").strip()
KEY_LOCATION = f"{BASE}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"


def file_to_url(path: str) -> str | None:
    if not path.endswith(".html") or path == "404.html":
        return None
    slug = path[:-5]
    if slug == "index":
        return BASE + "/"
    if slug == "en/index":
        return BASE + "/en"
    return f"{BASE}/{slug}"


def changed_since(ref: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{ref}..HEAD"], capture_output=True, text=True
    ).stdout.split()
    return [u for u in (file_to_url(p) for p in out) if u]


def from_sitemap() -> list[str]:
    xml = Path("sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*", help="/qa のようなパス、または完全なURL")
    ap.add_argument("--changed-since", metavar="REF", help="このgit refとの差分から拾う")
    ap.add_argument("--sitemap", action="store_true", help="sitemap の全URLを送る")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    urls: list[str] = []
    if args.changed_since:
        urls += changed_since(args.changed_since)
    if args.sitemap:
        urls += from_sitemap()
    urls += [u if u.startswith("http") else BASE + ("" if u.startswith("/") else "/") + u
             for u in args.urls]
    urls = sorted(set(urls))

    if not urls:
        print("送るURLがありません。--changed-since main か、URLを直接指定してください。")
        return 1
    if len(urls) > 10000:
        print(f"URLが多すぎます（{len(urls)}）。IndexNow の上限は1回10,000件です。")
        return 1

    print(f"{len(urls)} 件を IndexNow へ送信します:")
    for u in urls[:20]:
        print("  ", u)
    if len(urls) > 20:
        print(f"   … 他 {len(urls) - 20} 件")

    if args.dry_run:
        print("\n--dry-run のため送信しませんでした。")
        return 0

    payload = json.dumps(
        {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
    ).encode()
    req = urllib.request.Request(
        ENDPOINT, data=payload, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            print(f"\nHTTP {res.status} — {'受理されました' if res.status in (200, 202) else '確認してください'}")
    except Exception as e:  # noqa: BLE001 — surface whatever the endpoint said
        print(f"\n送信に失敗しました: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
