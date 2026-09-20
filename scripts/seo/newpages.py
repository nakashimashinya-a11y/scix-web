#!/usr/bin/env python3
"""新規ページ（毎週足すコラム）を「毎日の記録 → 週次の方針 → 効果測定」に載せるための共通部品。

公開されているページの一覧・公開日は **git の ref（既定 origin/main）** から読む。作業ツリーの状態
（別ブランチに居る・未コミットの原稿がある）に左右されない。追加 API は使わない＝台帳と git だけ。

  公開日 = Article JSON-LD の datePublished。無ければ git でそのファイルが最初に足されたコミットの日付。
  3言語版（column-x.html / en/column-x.html / zh-column-x.html）は同じ slug（column-x）にまとまる。
"""
from __future__ import annotations  # launchd の python3 は 3.9
import datetime
import functools
import os
import re
import subprocess

from common import LEDGER, REPO, d, daterange, file_to_url, jload, path_of

NEW_CLASSES = ("new-column", "new-page")
# ページでないもの（検索に出さない・sitemap に載せない）。noindex のファイルも site_pages() が落とす
NOT_PAGE_FILES = {"404.html", "thanks.html", "en/thanks.html", "zh-thanks.html"}
PAGE_FILE_RE = re.compile(r"^(en/)?[a-z0-9][a-z0-9-]*\.html$")
LANG_ORDER = {"ja": 0, "en": 1, "zh": 2}


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=120).stdout
    except Exception:  # noqa: BLE001 — git が無い・リポジトリが無いときは空（呼ぶ側は空でも動く）
        return ""


@functools.lru_cache(maxsize=None)
def ref() -> str:
    """読む対象。本番＝origin/main。無ければ HEAD（試験用に SCIX_WEB_REF で差し替えられる）。"""
    for r in (os.environ.get("SCIX_WEB_REF"), "origin/main", "HEAD"):
        if r and git("rev-parse", "--verify", "--quiet", r + "^{commit}").strip():
            return r
    return "HEAD"


def is_page_file(rel: str) -> bool:
    return bool(PAGE_FILE_RE.match(rel)) and rel not in NOT_PAGE_FILES and file_to_url(rel) is not None


def page_path(rel: str) -> str:
    """column-x.html → /column-x ・ en/index.html → /en"""
    return path_of(file_to_url(rel) or "")


def lang_of(path: str) -> str:
    if path == "/en" or path.startswith("/en/"):
        return "en"
    if path == "/zh" or path.startswith("/zh-"):
        return "zh"
    return "ja"


def base_slug(path: str) -> str:
    """3言語をまとめる鍵。/en/column-x・/zh-column-x・/column-x → column-x"""
    if path in ("/", "/en", "/zh"):
        return "index"
    if path.startswith("/en/"):
        return path[4:]
    if path.startswith("/zh-"):
        return path[4:]
    return path.lstrip("/")


def is_column(path: str) -> bool:
    return base_slug(path).startswith("column-")


@functools.lru_cache(maxsize=None)
def added_commits() -> dict:
    """{ファイル: (最初に足された日, sha, コミットの件名)}。改名は「消して足した」と数える＝URL が新しい。"""
    out = git("log", ref(), "--no-renames", "--diff-filter=A", "--name-only",
              "--format=@%cs%x09%H%x09%s", "--", "*.html")
    res, cur = {}, None
    for line in out.splitlines():
        if line.startswith("@"):
            parts = line[1:].split("\t", 2)
            cur = (parts[0], parts[1], parts[2] if len(parts) > 2 else "")
        elif line.strip() and cur:
            res[line.strip()] = cur  # log は新しい順＝後から来る古いコミットで上書きして「最初」を残す
    return res


@functools.lru_cache(maxsize=None)
def jsonld_published() -> dict:
    out = git("grep", "-o", "-E", r'"datePublished"[[:space:]]*:[[:space:]]*"[0-9]{4}-[0-9]{2}-[0-9]{2}',
              ref(), "--", "*.html")
    res = {}
    for line in out.splitlines():
        parts = line.split(":", 2)  # <ref>:<path>:<match>
        if len(parts) == 3:
            res.setdefault(parts[1], parts[2][-10:])
    return res


@functools.lru_cache(maxsize=None)
def site_pages() -> tuple:
    """ref にあるページの一覧。[{file, page, lang, slug, published, published_by}]"""
    files = [f for f in git("ls-tree", "-r", "--name-only", ref()).splitlines() if is_page_file(f)]
    noindex = {l.split(":", 1)[1] for l in git("grep", "-l", "-i", "-E", r'name="robots"[^>]*noindex',
                                                ref(), "--", "*.html").splitlines() if ":" in l}
    pub, added = jsonld_published(), added_commits()
    rows = []
    for f in files:
        if f in noindex:
            continue
        p = page_path(f)
        date, by = (pub[f], "jsonld") if f in pub else ((added[f][0], "git") if f in added else (None, None))
        rows.append({"file": f, "page": p, "lang": lang_of(p), "slug": base_slug(p),
                     "published": date, "published_by": by})
    return tuple(rows)


@functools.lru_cache(maxsize=None)
def ja_only_columns() -> frozenset:
    m = re.search(r"JA_ONLY_COLUMNS\s*=\s*\[(.*?)\]", git("show", f"{ref()}:header.js"), re.S)
    return frozenset(re.findall(r"'(/column-[a-z0-9-]+)'", m.group(1))) if m else frozenset()


# ---------------------------------------------------------------- 台帳（GSC・健診）

def latest_health():
    files = sorted((LEDGER / "health").glob("????-??-??.json"))
    return jload(files[-1]) if files else None


def inbound_counts(health) -> dict:
    """サイト内でそのページを指しているページ数（自分自身へのリンクは数えない）。"""
    out = {}
    for p in (health or {}).get("pages", []):
        for l in set(p.get("internal_links") or []):
            if l != p["url"]:
                out[l] = out.get(l, 0) + 1
    return out


def gsc_page_sums(start: datetime.date, end: datetime.date):
    """期間内のページ別 表示・クリックと、最初に表示が出た日。返り値 (sums, first_shown, データのある日数)"""
    sums, first, days = {}, {}, 0
    for day in daterange(start, end):
        g = jload(LEDGER / "gsc" / f"{day}.json")
        if not g:
            continue
        days += 1
        for p in g.get("pages", []):
            a = sums.setdefault(p["page"], {"impressions": 0, "clicks": 0})
            a["impressions"] += p["impressions"]; a["clicks"] += p["clicks"]
            if p["impressions"] > 0 and p["page"] not in first:
                first[p["page"]] = str(day)
    return sums, first, days


def peer_columns(lang: str, exclude, health=None) -> list:
    """同じ言語の既存コラム（sitemap＝健診のページ一覧から。表示ゼロのコラムも母集団に入れる）。"""
    ex = set(exclude)
    urls = [p["url"] for p in (health or {}).get("pages", []) if p.get("status") == 200]
    if not urls:
        urls = [r["page"] for r in site_pages()]
    return [u for u in urls if is_column(u) and lang_of(u) == lang and u not in ex]


def days_since(date_str, today_: datetime.date):
    return (today_ - d(date_str)).days if date_str else None
