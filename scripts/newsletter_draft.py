#!/usr/bin/env python3
"""週1本の更新メール（ブラストメール）に貼る本文の下書きを、ナレッジのカードから作る。

    python3 scripts/newsletter_draft.py           # 最新1本
    python3 scripts/newsletter_draft.py --n 2     # 最新2本

出力は 件名 と 本文（プレーンテキスト）。ブラストメールの新規配信に貼り、宛先は「全登録者」
（2026-09-16 中島運用）。解除リンクはブラストメールが末尾に付ける。数字も文言もカードの
h3/説明文をそのまま使う（ここで新しい主張を書かない）。
⚠️ 先頭の `{name}様` はプレースホルダ。ブラストメールの差し込みタグ（氏名＝項目 c0）に置き換えるか、
   宛名を付けないなら行ごと消す。タグの書式はブラストメールの編集画面で確認する。
"""
import re
import sys
import html
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_knowledge_jsonld import ja_cards  # noqa: E402

BASE = "https://www.scix.co.jp"


def main() -> int:
    n = 1
    if "--n" in sys.argv:
        n = int(sys.argv[sys.argv.index("--n") + 1])
    src = Path("knowledge.html").read_text(encoding="utf-8")
    cards = [c for c in ja_cards(src) if c["date"]]
    cards.sort(key=lambda c: (c["date"], c["num"]), reverse=True)
    picks = cards[:n]
    if not picks:
        print("カードが見つかりません", file=sys.stderr)
        return 1
    top = picks[0]
    subject = f"【ScienceX ナレッジ】{top['title'].split(' — ')[0]}"
    lines = ["{name}様", "", "サイエンスエックスの中島です。今週の記事をお送りします。", ""]
    for c in picks:
        lines += [f"■ {c['title']}", f"{BASE}{c['href']}", "", c["desc"], ""]
    lines += [
        "――",
        "販売中の案件一覧（NDA不要）",
        f"{BASE}/projects",
        "ナレッジ（全記事）",
        f"{BASE}/knowledge",
        "",
        "サイエンスエックス株式会社 代表取締役 中島 晋也（工学博士）",
        "〒103-0016 東京都中央区日本橋小網町8-2 BIZMARKS日本橋茅場町",
        "TEL 03-6691-3484 / s@scix.co.jp",
        "",
        "※このメールは scix.co.jp で登録いただいた方にお送りしています。配信の停止は末尾の解除リンクからお願いします。",
    ]
    print("件名: " + subject)
    print("（{name}様 はブラストメールの差し込みタグに置き換える）")
    print()
    print(html.unescape("\n".join(lines)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
