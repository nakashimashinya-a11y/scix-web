#!/usr/bin/env python3
"""GA4 Data API 用のトークンを1回だけ取る（analytics.readonly）。

Search Console のトークンと同じ OAuth クライアントを使い、ブラウザで中島さんが許可を押すと
`~/.config/scix-cockpit/ga4_token.json` に保存される。以後は refresh_token で自動更新。

    python3 scripts/seo/ga4_auth.py            # URL を表示して localhost で応答を待つ（最長24時間）
    python3 scripts/seo/ga4_auth.py --check    # 取得済みトークンで GA4 を1回読んで確かめる
"""
import http.server
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CFG, GA4_TOKEN, SC_TOKEN, Google, ga4_report, jload, log  # noqa: E402

SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
PORT = int(os.environ.get("GA4_AUTH_PORT", "8765"))


def check() -> int:
    g = Google(GA4_TOKEN)
    rows = ga4_report(g, "7daysAgo", "yesterday", ["date"], ["sessions", "keyEvents:generate_lead"])
    for r in sorted(rows, key=lambda x: x["date"]):
        print(r["date"], "sessions", r["sessions"], "leads", r.get("keyEvents:generate_lead"))
    print("OK GA4 を読めた")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return check()
    base = jload(SC_TOKEN)
    if not base:
        print(f"Search Console のトークンが無い: {SC_TOKEN}", file=sys.stderr)
        return 1
    client_id, client_secret = base["client_id"], base["client_secret"]
    redirect = f"http://localhost:{PORT}/"
    state = secrets.token_urlsafe(16)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
        "login_hint": "s@scix.co.jp",
    })
    print("次のURLを s@scix.co.jp でログインしたブラウザで開いて許可してください:\n\n" + url + "\n", flush=True)

    result = {}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):  # 静かに
            pass

        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] != state or "code" not in q:
                self.send_response(400); self.end_headers(); self.wfile.write(b"bad request")
                return
            result["code"] = q["code"][0]
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write("<h2>GA4 の許可を受け取りました。このタブは閉じて構いません。</h2>".encode())

    srv = http.server.HTTPServer(("127.0.0.1", PORT), H)
    srv.timeout = 24 * 3600
    srv.handle_request()
    if "code" not in result:
        print("許可が届かなかった（タイムアウト）", file=sys.stderr)
        return 1
    data = urllib.parse.urlencode({
        "code": result["code"], "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect, "grant_type": "authorization_code",
    }).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30) as res:
        tok = json.load(res)
    if "refresh_token" not in tok:
        print("refresh_token が返らなかった（prompt=consent を付けても出ない場合は Google 側で当アプリの許可を取り消してから再実行）", file=sys.stderr)
        return 1
    out = {
        "token": tok["access_token"], "refresh_token": tok["refresh_token"],
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id, "client_secret": client_secret,
        "scopes": [SCOPE], "universe_domain": "googleapis.com", "account": "s@scix.co.jp",
    }
    CFG.mkdir(parents=True, exist_ok=True)
    fd = os.open(GA4_TOKEN, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(out, f, indent=1)
    log(f"保存した: {GA4_TOKEN}")
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
