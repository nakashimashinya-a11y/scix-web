#!/usr/bin/env python3
"""Sync sitemap.xml <lastmod> values to each page's last git commit date.

Run from the repo root after publishing or editing pages:

    python3 scripts/sync_sitemap_lastmod.py          # report only
    python3 scripts/sync_sitemap_lastmod.py --write  # apply

Only <lastmod> is touched. URLs, hreflang clusters and <priority> are left
alone — adding or removing a <url> block is still a manual edit.

WARNING: this reads the last commit date, which cannot tell a content change
from a site-wide metadata sweep. Run the report first, and do NOT --write right
after a commit that touched many files for non-content reasons (a JSON-LD pass,
a link fix, a font cleanup) — it would stamp every page as updated today and
turn the sitemap's freshness signal into noise. In that situation, edit the
handful of genuinely-changed entries by hand instead.
"""
import re
import subprocess
import sys
from pathlib import Path

SITEMAP = Path("sitemap.xml")
BASE = "https://www.scix.co.jp"


def url_to_file(url: str) -> Path | None:
    """Resolve a public URL back to the HTML file Vercel serves for it."""
    path = url[len(BASE):] or "/"
    if path == "/":
        return Path("index.html")
    if path == "/en":
        return Path("en/index.html")
    candidate = Path(path.lstrip("/") + ".html")
    return candidate if candidate.exists() else None


def git_date(path: Path) -> str | None:
    out = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    return out or None


def main() -> int:
    write = "--write" in sys.argv
    text = SITEMAP.read_text(encoding="utf-8")
    block = re.compile(
        r"(<loc>(?P<url>[^<]+)</loc>.*?<lastmod>)(?P<date>[^<]+)(</lastmod>)",
        re.S,
    )

    changes: list[tuple[str, str, str]] = []
    unresolved: list[str] = []

    def repl(m: re.Match) -> str:
        url = m.group("url")
        f = url_to_file(url)
        if f is None:
            unresolved.append(url)
            return m.group(0)
        new = git_date(f)
        if not new or new == m.group("date"):
            return m.group(0)
        changes.append((url, m.group("date"), new))
        return m.group(1) + new + m.group(4)

    updated = block.sub(repl, text)

    for url, old, new in changes:
        print(f"{url}\n    {old} -> {new}")
    for url in unresolved:
        print(f"!! ファイルが見つかりません: {url}")

    print(f"\n更新 {len(changes)} 件 / 未解決 {len(unresolved)} 件")
    if write and changes:
        SITEMAP.write_text(updated, encoding="utf-8")
        print("sitemap.xml に書き込みました。")
    elif changes:
        print("（--write を付けると反映します）")
    return 1 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
