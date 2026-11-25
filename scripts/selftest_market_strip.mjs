// 読み物の頁の終わりの、写真つきの案件の帯（/market-strip.js・header.js の 7g）を、本物の Chrome（ヘッドレス）で確かめる試験（2026-11-25）。
// 外へは出ない（手元で配信して読むだけ・マーケットへの要求は Chrome の中で差し止めて作り物のカードで答える）。
//   node scripts/selftest_market_strip.mjs
//   CHROME_BIN=/path/to/chrome node …                 # Chrome の場所を指す（無ければ試験は飛ばす）
//   CARDS_JSON=<file> SHOTS=<dir> node …              # 手元で見た目を写すとき: 口の答えをその JSON で返し、頁の写しを <dir> に置く（倉には置かない）
//   NEEDS_JSON=<file> …                                # 同じく、買主のリクエストの口の答え
// 見ること:
//  ・出す頁（市場ノートの入口・速報・月号・市場データ・ナレッジ・半分のコラム）に、帯が1つ・カード4枚・「一覧を見る」が出る
//  ・出さない頁（残りの半分のコラム・土地の持ち主向けの4本・英語・中国語・トップ・/market-data・お問い合わせ）には出ない（部品も読まない）
//  ・半分の分け方: header.js の stripWanted が、式 sum(ord(ch) for ch in slug) % 2 == 0 と全部のコラムで合う
//  ・写真のある物を先に・限定の物は使わない・口が読めない／0枚のときは何も出さない（枠も見出しも）
//  ・帯のリンクを押すと ?src=<頁の印> が付き、GA4 の market_click は placement=strip（マーケットが読める印の形）
//  ・価格の字が出ない・携帯の幅で頁が横に広がらない・トップのカード（#top-cards）は今のまま
//  ・2026-11-25（2）: 会社案内（「3つの入口」のすぐ後）・買い手向けの頁・読み物の残り・柱の頁に案件の帯、売りたい方の頁（「売り方は2つ」のすぐ後）に買主のリクエストの帯
//    （札3枚・決まった選択肢の行だけ＝口に価格や自由に書いた文の行があっても出さない・番号の形が違う物と行の足りない物は使わない・押すと /needs へ）。
//    /grid-storage・/fund・/partners・報道の頁・送信後の頁・方針の頁・広告の着地の頁・英語と中国語の会社案内には出さない
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const chromeBin = [process.env.CHROME_BIN, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium'].filter(Boolean).find((x) => fs.existsSync(x));
if (!chromeBin) { console.log('SKIP: Chrome が見つからない（CHROME_BIN で指す）'); process.exit(0); }
const SHOTS = process.env.SHOTS || '';
const REAL = process.env.CARDS_JSON ? fs.readFileSync(process.env.CARDS_JSON, 'utf8') : '';
const REAL_NEEDS = process.env.NEEDS_JSON ? fs.readFileSync(process.env.NEEDS_JSON, 'utf8') : '';

// ---- 作り物のカード（実在の案件ではない・番号も名前も試験用） ----
const fake = (i, o = {}) => ({ id: 'TS-' + (i + 1), name: '試験の案件' + (i + 1), pref: '試験県', muni: '試験市', voltage: i % 3 ? '高圧' : '特別高圧', saleType: '完成渡し', mw: 2, capacityMwh: 8, img: 'cover', recommend: i === 0, viewersTotal: 5, gs: { level: 0, steps: [{ key: 'study' }, { key: 'apply' }] }, ...o });
const CARDS = {
  normal: { cards: [fake(0, { img: '' }), fake(1, { img: '' }), fake(2, { locked: true }), fake(3), fake(4), fake(5, { img: 'sat' }), fake(6), fake(7)] },
  empty: { cards: [] }
};
// ---- 作り物の買主のリクエスト（実在のリクエストではない）。出してはいけない行（価格・自由に書いた文）も混ぜておく ----
const fakeNeed = (i, o = {}) => ({ id: 'TW-' + (i + 1), profile: { capital: '試験の資本', listed: '試験の区分', industry: '試験の業種', sales: '試験の売上' }, has_price: true, posted: '2026-01-01', rows: [
  { k: 'price', label: '売却価格', value: '9億円（税抜）', must: 'must' }, { k: 'memo', label: '補足', value: '自由に書いた文', must: 'note' },
  { k: 'grid_stage', label: '電力の手続き', value: '試験の段' + (i + 1), must: 'must' }, { k: 'cod', label: '運転開始', value: '2099年3月まで', must: 'must' },
  { k: 'sale_type', label: '買い方', value: '権利渡し', must: 'soft' }, { k: 'voltage', label: '電圧', value: '高圧', must: 'must' }, { k: 'grid_area', label: 'エリア', value: '試験のエリア', must: 'must' }], ...o });
const NEEDS = {
  normal: { needs: [fakeNeed(0), fakeNeed(1, { id: 'bad id' }), fakeNeed(2, { rows: [{ k: 'voltage', label: '電圧', value: '高圧', must: 'must' }, { k: 'price', label: '売却価格', value: '9億円（税抜）', must: 'must' }] }), fakeNeed(3, { profile: null }), fakeNeed(4), fakeNeed(5)] },
  empty: { needs: [] }
};

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
const port = 9800 + Math.floor(Math.random() * 500);
const udir = fs.mkdtempSync(path.join(os.tmpdir(), 'scix-strip-test-'));
const chrome = spawn(chromeBin, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${udir}`, '--no-first-run', '--disable-gpu', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
let wsUrl = '';
for (let i = 0; i < 80 && !wsUrl; i++) { await sleep(250); try { wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json/version`)).json()).webSocketDebuggerUrl; } catch { /* まだ */ } }
if (!wsUrl) { chrome.kill(); server.close(); console.error('Chrome の口が開かない'); process.exit(1); }
const ws = new WebSocket(wsUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
let seq = 0; const waiting = new Map(); const onEvent = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && waiting.has(m.id)) { const { res, rej } = waiting.get(m.id); waiting.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); } else if (m.method && m.sessionId && onEvent.has(m.sessionId)) onEvent.get(m.sessionId)(m); };
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const id = ++seq; waiting.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params, sessionId })); setTimeout(() => { if (waiting.has(id)) { waiting.delete(id); rej(new Error('timeout ' + method)); } }, 30000); });

// cards＝'normal'・'empty'・'fail'（口が落ちている）。写真（/api/open/photo）は、作り物のときは落とす（電圧ごとの絵に替わる）・CARDS_JSON のときは本物を通す
async function page({ w = 1440, h = 900, mobile = false, cards = 'normal' } = {}) {
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
  const S = (m, p) => send(m, p, sessionId);
  const seen = [];
  onEvent.set(sessionId, (m) => {
    if (m.method !== 'Fetch.requestPaused') return;
    const u = new URL(m.params.request.url), id = m.params.requestId;
    seen.push(u.pathname);
    if (u.pathname === '/api/open/cards' && cards !== 'fail') {
      const hd = [{ name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Content-Type', value: 'application/json' }];
      const body = REAL && cards === 'normal' ? REAL : JSON.stringify(CARDS[cards]);
      return S('Fetch.fulfillRequest', { requestId: id, responseCode: 200, responseHeaders: hd, body: Buffer.from(body).toString('base64') }).catch(() => {});
    }
    if (u.pathname === '/api/open/needs' && cards !== 'fail') {
      const hd = [{ name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Content-Type', value: 'application/json' }];
      const body = REAL_NEEDS && cards === 'normal' ? REAL_NEEDS : JSON.stringify(NEEDS[cards]);
      return S('Fetch.fulfillRequest', { requestId: id, responseCode: 200, responseHeaders: hd, body: Buffer.from(body).toString('base64') }).catch(() => {});
    }
    if (REAL && u.pathname === '/api/open/photo') return S('Fetch.continueRequest', { requestId: id }).catch(() => {});
    return S('Fetch.failRequest', { requestId: id, errorReason: 'BlockedByClient' }).catch(() => {});
  });
  await S('Fetch.enable', { patterns: [{ urlPattern: 'https://dealroom.scix.co.jp/*', requestStage: 'Request' }, { urlPattern: '*googletagmanager*', requestStage: 'Request' }, { urlPattern: '*licdn*', requestStage: 'Request' }] });
  await S('Page.enable'); await S('Runtime.enable');
  await S('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile });
  return {
    S, seen,
    async go(url) {
      await S('Page.navigate', { url });
      for (let i = 0; i < 40; i++) { await sleep(250); try { if (await this.eval(`document.readyState === 'complete' && !!document.querySelector('header.scix-header')`)) break; } catch { /* まだ */ } }
      await sleep(400);
      // 帯は画面に近づいたら読む＝下まで送ってから待つ
      await this.eval(`(() => { const f = document.querySelector('footer'); window.scrollTo(0, f ? f.getBoundingClientRect().top + scrollY - innerHeight : document.body.scrollHeight); })()`);
      await sleep(1200);
    },
    async eval(expr) { const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description || '')); return r.result.value; },
    async shot(name) {
      if (!SHOTS) return;
      // 帯があれば、帯の前後 300px を含めて写す（無ければ下の帯の上 900px）
      const c = await this.eval(`(() => { const s = document.querySelector('.mks-wrap') || document.querySelector('footer'); s.scrollIntoView({ block: 'center' }); const r = s.getBoundingClientRect(); const top = Math.max(0, r.top + scrollY - (s.matches('footer') ? 900 : 300)); return { x: 0, y: top, width: innerWidth, height: (s.matches('footer') ? 900 + 200 : r.height + 600), scale: 1 }; })()`); await sleep(1500);
      const r = await S('Page.captureScreenshot', { format: 'png', clip: c, captureBeyondViewport: true }); fs.mkdirSync(SHOTS, { recursive: true }); fs.writeFileSync(path.join(SHOTS, name + '.png'), Buffer.from(r.data, 'base64'));
    },
    async close() { onEvent.delete(sessionId); try { await send('Target.closeTarget', { targetId }); } catch { /* 閉じ済み */ } }
  };
}

let pass = 0; const fails = [];
const ok = (name, cond, extra = '') => { if (cond) pass++; else { fails.push(name + ' ' + extra); console.log('FAIL', name, extra); } };
const STATE = `(() => {
  const s = document.querySelectorAll('.mks'), b = s[0];
  const o = { n: s.length, cards: b ? b.querySelectorAll('article.sc').length : 0, ids: b ? [...b.querySelectorAll('article.sc')].map((a) => a.getAttribute('data-id')) : [],
    head: b ? (b.querySelector('.mks-h') || {}).textContent : '', more: b ? !!b.querySelector('.mks-more a[href="https://dealroom.scix.co.jp/"]') : false,
    loaded: !!document.querySelector('script[src="/market-strip.js"]'), slot: document.querySelectorAll('.mks-slot').length,
    price: b ? /[0-9]\\s*(億|万)?円|税抜|税込|指値/.test(b.textContent) : false, placement: b ? b.getAttribute('data-placement') : '',
    scrollW: document.documentElement.scrollWidth, W: innerWidth, top: !!document.querySelector('#top-cards'),
    kind: b ? (b.classList.contains('mkn') ? 'needs' : 'deals') : '', ncards: b ? b.querySelectorAll('article.mkn-c').length : 0, nids: b ? [...b.querySelectorAll('article.mkn-c')].map((a) => a.getAttribute('data-id')) : [],
    moreNeeds: b ? !!b.querySelector('.mks-more a[href="https://dealroom.scix.co.jp/needs"]') : false, text: b ? b.textContent : '',
    prev: b && b.closest('.mks-wrap') && b.closest('.mks-wrap').previousElementSibling ? b.closest('.mks-wrap').previousElementSibling.id || '' : '',
    next: b && b.closest('.mks-wrap') && b.closest('.mks-wrap').nextElementSibling ? b.closest('.mks-wrap').nextElementSibling.id || b.closest('.mks-wrap').nextElementSibling.className || b.closest('.mks-wrap').nextElementSibling.tagName : '' };
  if (b) { const h1 = document.querySelector('h1'); o.afterH1 = !h1 || !!(h1.compareDocumentPosition(b) & 4); const ft = document.querySelector('footer'); o.beforeFooter = !ft || !!(b.compareDocumentPosition(ft) & 4); }
  return o;
})()`;

// ---- 1. 出す頁・出さない頁 ----
const colSlugs = fs.readdirSync(ROOT).filter((f) => /^column-[a-z0-9-]+\.html$/.test(f)).map((f) => f.slice('column-'.length, -5)).sort();
const LAND = new Set(['land-buyback', 'land-lease', 'land-value', 'land-zoning']);
const want = (slug) => !LAND.has(slug) && [...slug].reduce((a, ch) => a + ch.charCodeAt(0), 0) % 2 === 0;
const onCol = colSlugs.filter(want), offCol = colSlugs.filter((s) => !LAND.has(s) && !want(s));
const guides = fs.readdirSync(ROOT).filter((f) => /^guide-[a-z0-9-]+\.html$/.test(f)).map((f) => '/' + f.slice(0, -5)).sort();
const MORE = ['/company', '/transfer', '/investors', '/for/major', '/for/sme', '/qa', '/faq', '/glossary', ...guides];   // 2026-11-25（2）で足した、案件の帯の頁
const YES = ['/research', '/research/flash', '/research/data', '/knowledge', ...fs.readdirSync(path.join(ROOT, 'research')).filter((d) => /^\d{4}-\d{2}$/.test(d)).slice(-1).map((d) => '/research/' + d), '/column-' + onCol[0], '/column-' + onCol[onCol.length - 1], ...MORE];
const NO = ['/', '/en', '/zh', '/market-data', '/contact', '/sell-form', '/en/knowledge', '/column-' + offCol[0], '/column-land-value', '/column-land-buyback',
  '/grid-storage', '/fund', '/partners', '/press', '/newsroom', '/thanks', '/privacy', '/lp/sell', '/lp/buy', '/en/company', '/zh-company', '/en/sourcing', '/en/transfer', '/en/qa', '/zh-qa'].filter((u) => u.length < 4 || fs.existsSync(path.join(ROOT, u.slice(1) + '.html')) || fs.existsSync(path.join(ROOT, u.slice(1), 'index.html')));
if (fs.existsSync(path.join(ROOT, 'en', 'column-' + onCol[0] + '.html'))) NO.push('/en/column-' + onCol[0]);
for (const url of YES) {
  const p = await page(); await p.go(BASE + url); const s = await p.eval(STATE); const at = `[${url}] `;
  ok(at + '帯が1つ・カード4枚・見出し・一覧へのリンク', s.n === 1 && s.cards === 4 && s.head === 'いま売りに出ている蓄電所' && s.more, JSON.stringify(s));
  ok(at + '本文の後・下の帯の前', s.afterH1 && s.beforeFooter, JSON.stringify(s));
  ok(at + '価格の字が無い・入れ物は data-placement=strip', !s.price && s.placement === 'strip', JSON.stringify(s));
  ok(at + '写真のある物を先に・限定は使わない', REAL || JSON.stringify(s.ids) === JSON.stringify(['TS-4', 'TS-5', 'TS-6', 'TS-7']), JSON.stringify(s.ids));
  ok(at + '案件の帯（買主のリクエストの帯ではない）', s.kind === 'deals' && s.ncards === 0, JSON.stringify(s));
  if (url === '/company') ok(at + '「3つの入口」の段のすぐ後・代表メッセージの段の前', s.prev === 'entrances' && s.next === 'message', `${s.prev} / ${s.next}`);
  if (url === '/transfer' || url === '/investors' || url === '/glossary') ok(at + '下の案内の段の前', /(^|\s)cta(\s|$)/.test(s.next) || s.next === 'contact', `${s.prev} / ${s.next}`);
  await p.shot('pc' + url.replace(/\//g, '_'));
  await p.close();
}
// ---- 1b. 売りたい方の頁: 買主のリクエストの帯 ----
{
  const p = await page(); await p.go(BASE + '/sourcing'); const s = await p.eval(STATE); const at = '[/sourcing] ';
  ok(at + '買主のリクエストの帯が1つ・札3枚・見出し・一覧へのリンク', s.n === 1 && s.kind === 'needs' && s.ncards === 3 && s.cards === 0 && s.head === 'いま買主が探している蓄電所' && s.moreNeeds, JSON.stringify(s));
  ok(at + '「売り方は2つ」の段のすぐ後', s.prev === 'ways' && s.next === 'what', `${s.prev} / ${s.next}`);
  ok(at + '番号の形が違う物・行の足りない物は使わない（口の並びの頭から）', REAL_NEEDS || JSON.stringify(s.nids) === JSON.stringify(['TW-1', 'TW-4', 'TW-5']), JSON.stringify(s.nids));
  ok(at + '決まった選択肢の行だけ（価格・自由に書いた文・属性の売上は出さない）', !s.price && !/売却価格|自由に書いた文|試験の売上|補足/.test(s.text) && s.placement === 'strip', s.text.slice(0, 300));
  if (!REAL_NEEDS) {
    const c = await p.eval(`(() => { const a = document.querySelector('.mkn article.mkn-c'); return { who: a.querySelector('.mkn-who b').textContent, labels: [...a.querySelectorAll('dt')].map((x) => x.textContent), soft: a.querySelectorAll('.mkn-soft').length, href: a.querySelector('a.mkn-go').getAttribute('href'), who4: document.querySelectorAll('.mkn article.mkn-c')[1].querySelector('.mkn-who b').textContent }; })()`);
    ok(at + '札の中身: 属性・行の順・「相談できる」・行き先', c.who === '試験の資本・試験の区分・試験の業種' && JSON.stringify(c.labels) === JSON.stringify(['エリア', '電圧', '買い方', '運転開始', '電力の手続き']) && c.soft === 1 && c.href === 'https://dealroom.scix.co.jp/needs?need=TW-1' && c.who4 === '会社の概要は確認中', JSON.stringify(c));
  }
  await p.shot('pc_sourcing');
  await p.close();
}
for (const url of NO) {
  const p = await page(); await p.go(BASE + url); const s = await p.eval(STATE);
  ok(`[${url}] 帯を出さない・部品も読まない`, s.n === 0 && !s.loaded && s.slot === 0, JSON.stringify(s));
  if (url === '/column-land-value' || url === '/column-' + offCol[0]) await p.shot('pc' + url.replace(/\//g, '_'));
  await p.close();
}

// ---- 2. 半分の分け方: header.js の stripWanted と式が全部のコラムで合う ----
{
  const p = await page(); await p.go(BASE + '/knowledge');
  const got = await p.eval(`(${JSON.stringify(colSlugs)}).filter((s) => window.SCIX_STRIP_WANTED('/column-' + s))`);
  ok('半分の分け方が式と合う（全部のコラム）', JSON.stringify(got) === JSON.stringify(onCol), `${got.length}/${onCol.length}`);
  ok('出す側と出さない側がおおよそ半分ずつ', onCol.length > 0 && offCol.length > 0 && Math.abs(onCol.length - offCol.length) <= Math.ceil(colSlugs.length * 0.2), `${onCol.length}/${offCol.length}`);
  await p.close();
}

// ---- 3. 口が読めない・0枚のとき ----
for (const cards of ['fail', 'empty']) for (const url of ['/research/flash', '/company', '/sourcing']) {
  const p = await page({ cards }); await p.go(BASE + url); const s = await p.eval(STATE);
  ok(`[${url} 口が ${cards}] 何も出さない（枠も見出しも・仮の枠も残さない）`, s.loaded && s.n === 0 && s.slot === 0 && !(await p.eval(`!!document.querySelector('.mks-wrap, .mks-h, html[data-mks]')`)), JSON.stringify(s));
  await p.close();
}

// ---- 4. 印と GA4 ----
for (const [url, mark] of [['/column-' + onCol[0], 'col-' + onCol[0]], ['/research/flash', 'site-research-flash'], ['/knowledge', 'knowledge'],
  ['/company', 'site-company'], ['/sourcing', 'site-sourcing'], ['/for/major', 'site-for-major'], [guides[0], 'site-' + guides[0].slice(1)], ['/qa', 'site-qa']]) {
  const p = await page(); await p.go(BASE + url);
  const r = await p.eval(`(() => {
    window.__ev = []; window.gtag = function (a, b, c) { if (b === 'market_click') window.__ev.push(c); };
    document.addEventListener('click', (e) => e.preventDefault());
    const out = [], paths = [];
    for (const a of [document.querySelector('.mks article a'), document.querySelector('.mks .mks-more a')]) {
      a.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
      out.push(new URL(a.href).searchParams.get('src')); paths.push(new URL(a.href).pathname + (new URL(a.href).searchParams.get('need') ? '?need' : ''));
    }
    return { src: out, paths, ev: window.__ev.map((e) => e.placement + ':' + e.src_mark), link: window.__ev.map((e) => e.link_path) };
  })()`);
  if (url === '/sourcing') ok(`[${url}] 行き先はマーケットの /needs（札は ?need=<番号> つき）`, JSON.stringify(r.paths) === JSON.stringify(['/needs?need', '/needs']) && r.link.every((x) => x === '/needs'), JSON.stringify(r));
  else ok(`[${url}] 行き先は今までどおり（札は /deal・一覧は /）`, JSON.stringify(r.paths) === JSON.stringify(['/deal', '/']), JSON.stringify(r));
  const SITE_MARK_RX = /^(top|top-card|knowledge|report(-\d{4}-\d{2})?|(col|site)-[a-z0-9][a-z0-9-]{0,40})(-en|-zh)?$/;   // dealroom の functions/_lib/open_visits.ts と同じ
  ok(`[${url}] 押すと ?src=${mark}（マーケットが読める形）`, r.src.every((x) => x === mark && x.length <= 48 && SITE_MARK_RX.test(x)), JSON.stringify(r));
  ok(`[${url}] GA4 market_click は placement=strip`, r.ev.length === 2 && r.ev.every((x) => x === 'strip:' + mark), JSON.stringify(r));
  await p.close();
}

// ---- 5. 携帯の幅 ----
for (const url of ['/column-' + onCol[0], '/research/flash', '/knowledge', '/company', '/sourcing', '/qa', '/for/major', guides[0], '/faq']) {
  const p = await page({ w: 375, h: 812, mobile: true }); await p.go(BASE + url); const s = await p.eval(STATE);
  ok(`[${url} 375px] 帯が出る・頁が横に広がらない`, s.n === 1 && (url === '/sourcing' ? s.ncards === 3 : s.cards === 4) && s.scrollW <= s.W, JSON.stringify(s));
  await p.shot('sp' + url.replace(/\//g, '_'));
  await p.close();
}

try { ws.close(); } catch { /* 閉じ済み */ }
chrome.kill(); server.close(); await sleep(300); try { fs.rmSync(udir, { recursive: true, force: true }); } catch { /* 一時の置き場 */ }
console.log(`${pass}/${pass + fails.length} 通過`);
process.exit(fails.length ? 1 : 0);
