// 上の帯（header.js）の見た目と動きを、本物の Chrome（ヘッドレス）で確かめる試験（2026-11-23）。外へは出ない（手元で配信して読むだけ）。
//   node scripts/selftest_header.mjs            # 全部
//   CHROME_BIN=/path/to/chrome node …            # Chrome の場所を指す（無ければ試験は飛ばす）
// 見ること:
//  ・幅 320〜1920 × 日本語・英語・中国語: 帯の高さ 64px・頁が横に広がらない・札が折れない・広い帯（1101〜）は ロゴ → まとまり → 外の札 → ログイン → 言葉の切り替え の順で重ならず右にはみ出さない・畳んだメニュー（〜1100）は ロゴ → 言葉の切り替え → burger が1段
//  ・左上のロゴは3つの言葉とも同じ画像（/img/logo-navy.png）・まとまりの名前は蓄電所マーケットのトップへ
//  ・引き出しのある札（日本語: 買いたい・売りたい・ナレッジ・市場リサーチ／英語: ナレッジ・市場リサーチ）の動き:
//      マウス＝合わせると開く・下ろす途中で閉じない・押すと頁へ（preventDefault されない）・離れると閉じる（押して固定されない）・別の札に合わせると前の札は閉じる・外を押すと閉じる
//      指（hover なし）と畳んだメニュー＝1回目の押下で開き（頁は移らない）・2回目で頁へ
//      キーボード＝Enter は頁へ・↓ で開いて最初のリンクへ・Esc で閉じて札へ戻る・aria-expanded が開閉に合う
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const chromeBin = [process.env.CHROME_BIN, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium'].filter(Boolean).find((x) => fs.existsSync(x));
if (!chromeBin) { console.log('SKIP: Chrome が見つからない（CHROME_BIN で指す）'); process.exit(0); }

// ---- 手元の配信（cleanUrls つき） ----
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json', '.ico': 'image/x-icon', '.jpg': 'image/jpeg', '.webp': 'image/webp' };
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  for (const c of [p, p + '.html', path.join(p, 'index.html')]) {
    const f = path.join(ROOT, c);
    if (f.startsWith(ROOT) && fs.existsSync(f) && fs.statSync(f).isFile()) { res.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); return fs.createReadStream(f).pipe(res); }
  }
  res.writeHead(404); res.end('not found');
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}`;

// ---- Chrome を DevTools の口で動かす ----
const port = 9300 + Math.floor(Math.random() * 500);
const udir = fs.mkdtempSync(path.join(os.tmpdir(), 'scix-header-test-'));
const chrome = spawn(chromeBin, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${udir}`, '--no-first-run', '--disable-gpu', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
let wsUrl = '';
for (let i = 0; i < 80 && !wsUrl; i++) { await sleep(250); try { wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json/version`)).json()).webSocketDebuggerUrl; } catch { /* まだ */ } }
if (!wsUrl) { chrome.kill(); server.close(); console.error('Chrome の口が開かない'); process.exit(1); }
const ws = new WebSocket(wsUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
let seq = 0; const waiting = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && waiting.has(m.id)) { const { res, rej } = waiting.get(m.id); waiting.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); } };
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const id = ++seq; waiting.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params, sessionId })); setTimeout(() => { if (waiting.has(id)) { waiting.delete(id); rej(new Error('timeout ' + method)); } }, 30000); });
async function page({ w, h = 800, mobile = false, touch = false }) {
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
  const S = (m, p) => send(m, p, sessionId);
  await S('Page.enable'); await S('Runtime.enable');
  await S('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile });
  if (touch) { await S('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 }); await S('Emulation.setEmitTouchEventsForMouse', { enabled: true, configuration: 'mobile' }); }
  return {
    S,
    async go(url) { await S('Page.navigate', { url }); for (let i = 0; i < 40; i++) { await sleep(250); try { if (await this.eval(`!!document.querySelector('header.scix-header .scix-lang')`)) break; } catch { /* まだ */ } } await sleep(500); },
    async eval(expr) { const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description || '')); return r.result.value; },
    async close() { try { await send('Target.closeTarget', { targetId }); } catch { /* 閉じ済み */ } }
  };
}

let pass = 0; const fails = [];
const ok = (name, cond, extra = '') => { if (cond) pass++; else { fails.push(name + ' ' + extra); console.log('FAIL', name, extra); } };

// ---- 1. 幅ごとの寸法 ----
const MEASURE = `(() => {
  const W = innerWidth, hdr = document.querySelector('header.scix-header');
  const o = { W, scrollW: document.documentElement.scrollWidth, hdrH: Math.round(hdr.getBoundingClientRect().height), bad: [] };
  const r = (s) => { const e = hdr.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return b.width ? { l: b.left, r: b.right } : null; };
  const logo = r('.scix-header-logo img'), mg = r('.scix-mg'), auth = r('.scix-auth'), lang = r('.scix-lang'), burger = r('.scix-header-burger');
  const lightEls = [...hdr.querySelectorAll('.scix-header-nav > a, .scix-header-nav > .scix-nav-dd')].filter((e) => e.getBoundingClientRect().width);
  const light = lightEls.length ? { l: lightEls[0].getBoundingClientRect().left, r: lightEls[lightEls.length - 1].getBoundingClientRect().right } : null;
  const lines = (el) => { const rg = document.createRange(); rg.selectNodeContents(el); return new Set([...rg.getClientRects()].filter((x) => x.width > 0).map((x) => Math.round(x.top / 4))).size; };
  for (const el of hdr.querySelectorAll('.scix-nav-main span, .scix-mg-name span, .scix-login span, .scix-mk, .scix-header-nav > a span')) if (el.getBoundingClientRect().width && lines(el) > 1) o.bad.push('折れ:' + el.textContent.trim().slice(0, 18));
  if (W > 1100) {
    const seq = [logo, mg, light, auth, lang];
    if (seq.some((x) => !x)) o.bad.push('部品が無い');
    else { for (let i = 1; i < seq.length; i++) if (seq[i].l < seq[i - 1].r + 2) o.bad.push('重なり:' + i); if (lang.r > W - 8) o.bad.push('右にはみ出し'); }
  } else {
    if (!(logo && lang && burger)) o.bad.push('部品が無い');
    else { if (lang.l < logo.r) o.bad.push('ロゴと言葉の切り替えが重なる'); if (burger.l < lang.r) o.bad.push('言葉の切り替えと burger が重なる'); if (burger.r > W) o.bad.push('burger がはみ出す'); }
  }
  o.logoSrc = hdr.querySelector('.scix-header-logo img').getAttribute('src'); o.logoHref = hdr.querySelector('.scix-header-logo').getAttribute('href');
  const nm = hdr.querySelector('.scix-mg-name'); o.nameHref = nm ? nm.getAttribute('href') : ''; o.mgLinks = hdr.querySelectorAll('.scix-mg .scix-nav-main').length;
  return o;
})()`;
const PAGES = [['ja', '/', '/'], ['en', '/en', '/en'], ['zh', '/zh', '/zh']];
const WIDTHS = (process.env.WIDTHS || '320,375,420,768,1024,1100,1101,1180,1280,1366,1440,1920').split(',').map(Number);
for (const [lg, url, logoHref] of PAGES) for (const w of WIDTHS) {
  const p = await page({ w, h: 700, mobile: w < 500 }); await p.go(BASE + url);
  const m = await p.eval(MEASURE); const at = `[${lg} ${w}px] `;
  ok(at + '帯の高さ 64px', m.hdrH === 64, String(m.hdrH));
  ok(at + '頁が横に広がらない', m.scrollW <= m.W, `${m.scrollW}>${m.W}`);
  ok(at + '並び・はみ出し・折れ', m.bad.length === 0, m.bad.join(' / '));
  ok(at + 'ロゴは ScienceX の紺の版で固定・行き先は会社サイトのトップ', m.logoSrc === '/img/logo-navy.png' && m.logoHref === logoHref, `${m.logoSrc} ${m.logoHref}`);
  ok(at + 'まとまりの名前はマーケットのトップへ・買いたい／売りたいの2つ', /dealroom\.scix\.co\.jp\/(en)?$/.test(m.nameHref) && m.mgLinks === 2, `${m.nameHref} ${m.mgLinks}`);
  await p.close();
}

// ---- 2. 動き ----
const rectOf = (p, sel) => p.eval(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
const state = (p) => p.eval(`(() => { const o = {}; document.querySelectorAll('.scix-nav-dd').forEach((d) => { o[d.dataset.group] = [d.classList.contains('open'), d.querySelector('.scix-nav-dd-toggle').getAttribute('aria-expanded'), getComputedStyle(d.querySelector('.scix-nav-dd-menu')).display]; }); return o; })()`);
const watch = (p) => p.eval(`(() => { window.__dp = []; document.addEventListener('click', (e) => { const a = e.target.closest && e.target.closest('a'); if (a && a.closest('#scix-header')) { window.__dp.push({ href: a.getAttribute('href'), dp: e.defaultPrevented }); e.preventDefault(); } }, false); })()`);
const mm = (p, x, y) => p.S('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y, button: 'none' });
const click = async (p, x, y) => { await mm(p, x, y); await p.S('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 }); await p.S('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 }); };
const key = async (p, k, vk) => { await p.S('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: k, code: k, windowsVirtualKeyCode: vk }); await p.S('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code: k, windowsVirtualKeyCode: vk }); };
const tap = async (p, x, y) => { await p.S('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] }); await p.S('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); await sleep(150); };

for (const [lg, url] of [['ja', '/'], ['en', '/en']]) {
  const groups = lg === 'ja' ? ['buy', 'sell', 'knowledge', 'research'] : ['knowledge', 'research'];
  const sel = (g) => `.scix-nav-dd[data-group=${g}] .scix-nav-dd-toggle`;
  {   // マウス（1440・hover あり）
    const p = await page({ w: 1440 }); await p.go(BASE + url); await watch(p); const at = `[マウス ${lg}] `;
    for (const g of groups) {
      const r = await rectOf(p, sel(g)); await mm(p, 5, 300); await sleep(250); await mm(p, r.x, r.y); await sleep(60);
      let st = await state(p); ok(at + `${g} 合わせると開く（aria-expanded=true）`, st[g][0] && st[g][1] === 'true' && st[g][2] !== 'none', JSON.stringify(st[g]));
      const first = await rectOf(p, `.scix-nav-dd[data-group=${g}] .scix-nav-dd-menu a`); let stayed = true;
      for (let i = 1; i <= 14; i++) { await mm(p, r.x + (first.x - r.x) * i / 14, r.y + (first.y - r.y) * i / 14); await sleep(25); st = await state(p); if (!st[g][0]) stayed = false; }
      await sleep(250); st = await state(p); ok(at + `${g} 下ろす途中・着いた後も閉じない`, stayed && st[g][0], JSON.stringify(st[g]));
      await mm(p, r.x, r.y); await sleep(60); await p.eval('window.__dp = []'); await click(p, r.x, r.y); await sleep(80);
      const dp = await p.eval('window.__dp'); ok(at + `${g} 札を押すと頁へ`, dp.length === 1 && dp[0].dp === false, JSON.stringify(dp));
      await mm(p, 5, 300); await sleep(350); st = await state(p); ok(at + `${g} 離れると閉じる（押して固定されない）`, !st[g][0] && st[g][1] === 'false', JSON.stringify(st[g]));
    }
    const a = await rectOf(p, sel('knowledge')), c = await rectOf(p, sel('research'));
    await mm(p, a.x, a.y); await sleep(60); await mm(p, c.x, c.y); await sleep(60); let st = await state(p); ok(at + '別の札に合わせると前の札は閉じる', !st.knowledge[0] && st.research[0], JSON.stringify(st));
    const gap = await p.eval(`(() => { const h = document.querySelector('.scix-auth').getBoundingClientRect(); const l = [...document.querySelectorAll('.scix-header-nav > a, .scix-header-nav > .scix-nav-dd')].pop().getBoundingClientRect(); return (h.left + l.right) / 2; })()`);
    await click(p, gap, 30); await sleep(100); st = await state(p); ok(at + '外を押すと閉じる', !st.research[0], JSON.stringify(st.research));
    await p.eval(`document.querySelector(${JSON.stringify(sel('research'))}).focus()`); await p.eval('window.__dp = []'); await key(p, 'Enter', 13); await sleep(80);
    const dpk = await p.eval('window.__dp'); ok(at + 'キーボード Enter は頁へ', dpk.length === 1 && dpk[0].dp === false, JSON.stringify(dpk));
    await key(p, 'ArrowDown', 40); await sleep(80); st = await state(p); const f1 = await p.eval(`document.activeElement.getAttribute('href')`);
    ok(at + 'キーボード ↓ で開いて最初のリンクへ', st.research[0] && st.research[1] === 'true' && /\/report$/.test(f1), JSON.stringify(st.research) + f1);
    await key(p, 'Escape', 27); await sleep(80); st = await state(p); ok(at + 'Esc で閉じて札へ戻る', !st.research[0] && st.research[1] === 'false' && /scix-nav-dd-toggle/.test(await p.eval('document.activeElement.className')), JSON.stringify(st.research));
    await p.close();
  }
  {   // 指（1280・hover なし）
    const p = await page({ w: 1280, touch: true }); await p.go(BASE + url); await watch(p); const at = `[指1280 ${lg}] `;
    ok(at + 'hover:none', (await p.eval(`matchMedia('(hover:hover)').matches`)) === false);
    for (const g of groups) {
      const r = await rectOf(p, sel(g)); await p.eval('window.__dp = []'); await tap(p, r.x, r.y);
      let st = await state(p), dp = await p.eval('window.__dp'); ok(at + `${g} 1回目の押下で開く（頁は移らない）`, st[g][0] && st[g][1] === 'true' && dp.length === 1 && dp[0].dp === true, JSON.stringify(st[g]) + JSON.stringify(dp));
      await p.eval('window.__dp = []'); await tap(p, r.x, r.y); dp = await p.eval('window.__dp'); ok(at + `${g} 2回目の押下で頁へ`, dp.length === 1 && dp[0].dp === false, JSON.stringify(dp));
      await p.go(BASE + url); await watch(p);
    }
    await p.close();
  }
  {   // 畳んだメニュー（375）
    const p = await page({ w: 375, h: 780, mobile: true, touch: true }); await p.go(BASE + url); await watch(p); const at = `[畳んだメニュー ${lg}] `;
    const bu = await rectOf(p, '#scix-header-burger'); await tap(p, bu.x, bu.y);
    ok(at + 'メニューが開く', await p.eval(`document.getElementById('scix-header').classList.contains('scix-header-open')`));
    const first = await p.eval(`(() => { const h = document.querySelector('.scix-header-nav'); const e = h.firstElementChild; return e.className; })()`);
    ok(at + '一番上はまとまり', /scix-mg/.test(first), first);
    for (const g of groups) {
      const r = await rectOf(p, sel(g)); await p.eval('window.__dp = []'); await tap(p, r.x, r.y);
      let st = await state(p), dp = await p.eval('window.__dp');
      ok(at + `${g} 1回目の押下で開く（頁は移らない・メニューは閉じない）`, st[g][0] && dp.length === 1 && dp[0].dp === true && (await p.eval(`document.getElementById('scix-header').classList.contains('scix-header-open')`)), JSON.stringify(st[g]) + JSON.stringify(dp));
      await p.eval('window.__dp = []'); await tap(p, r.x, r.y); dp = await p.eval('window.__dp'); ok(at + `${g} 2回目の押下で頁へ`, dp.length === 1 && dp[0].dp === false, JSON.stringify(dp));
      await p.go(BASE + url); await watch(p); const b2 = await rectOf(p, '#scix-header-burger'); await tap(p, b2.x, b2.y);
    }
    await p.close();
  }
}

try { ws.close(); } catch { /* 閉じ済み */ }
chrome.kill(); server.close(); await sleep(300); try { fs.rmSync(udir, { recursive: true, force: true }); } catch { /* 一時の置き場 */ }
console.log(`${pass}/${pass + fails.length} 通過`);
process.exit(fails.length ? 1 : 0);
