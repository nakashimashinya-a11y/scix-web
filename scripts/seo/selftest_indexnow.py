#!/usr/bin/env python3
"""scripts/seo/indexnow_ping.py の自己検査。IndexNow へは送らない（POST を差し替える）・本物の控えには触らない（一時の置き場）。

    python3 scripts/seo/selftest_indexnow.py        # 0=全部通った
"""
from __future__ import annotations  # launchd の python3 は 3.9
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import indexnow_ping as ip  # noqa: E402

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)


def main():
    calls = []
    ip.post = lambda key, urls: (calls.append(list(urls)), 200)[1]
    ip.today_jst = lambda: "2099-01-01"
    with tempfile.TemporaryDirectory() as td:
        sm = Path(td) / "sitemap.xml"
        sm.write_text(
            "<urlset>"
            "<url><loc>https://www.scix.co.jp/</loc><lastmod>2099-01-01</lastmod></url>"
            "<url><loc>https://www.scix.co.jp/old</loc><lastmod>2098-12-01</lastmod></url>"
            "<url><loc>https://www.scix.co.jp/new</loc><lastmod>2098-12-31</lastmod></url>"
            "<url><loc>https://example.com/x</loc><lastmod>2099-01-01</lastmod></url>"
            "</urlset>", encoding="utf-8")
        led = Path(td) / "sent.jsonl"
        base = ["--sitemap", str(sm), "--ledger", str(led), "--since", "2098-12-30"]

        # 送らない（--apply 無し）は POST も控えも無し
        check(ip.main(base) == 0 and not calls and not led.exists(), "--apply 無しで送った・控えを書いた")
        # 送る: lastmod が --since より新しい物と --extra だけ・host 外は外す・1回の POST
        check(ip.main(base + ["--apply", "--extra", "/llms.txt"]) == 0, "送る回が 0 で終わらない")
        check(len(calls) == 1, f"POST の回数 {len(calls)}")
        check(sorted(calls[0]) == ["https://www.scix.co.jp/", "https://www.scix.co.jp/llms.txt", "https://www.scix.co.jp/new"],
              f"送った住所 {calls[0] if calls else None}")
        rows = [json.loads(x) for x in led.read_text(encoding="utf-8").splitlines()]
        check(len(rows) == 3 and all(r["date"] == "2099-01-01" for r in rows), "控えの行が合わない")
        # 同じ日の2回目は送らない
        check(ip.main(base + ["--apply", "--extra", "/llms.txt"]) == 0 and len(calls) == 1, "同じ日に2度送った")
        # 次の日でも同じ lastmod は送らない（--extra は日付が変わるので送る）
        ip.today_jst = lambda: "2099-01-02"
        check(ip.main(base + ["--apply"]) == 0 and len(calls) == 1, "同じ lastmod を2度送った")
        # 失敗の返事は控えに書かない
        ip.post = lambda key, urls: 429
        led2 = Path(td) / "sent2.jsonl"
        check(ip.main(["--sitemap", str(sm), "--ledger", str(led2), "--since", "2098-12-30", "--apply"]) == 1 and not led2.exists(),
              "429 で控えを書いた")
    # 鍵は決まりの形で、根の <鍵>.txt の中身と同じ
    key = ip.load_key()
    check(ip.KEY_RX.match(key) is not None, "鍵の形")
    check((ip.ROOT / f"{key}.txt").read_text(encoding="utf-8").strip() == key, "鍵ファイルの中身")

    for f in FAILS:
        print("NG", f)
    print("selftest_indexnow:", "ok" if not FAILS else f"{len(FAILS)} 件 NG")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
