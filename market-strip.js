/* ======================================================
   読み物の頁の終わりの、写真つきの案件の帯（日本語の頁だけ）— 2026-11-25
   コードだけ。案件のデータは持たない（O16-19）。HTML には何も焼かない＝帯は画面が描くだけ（O07-60）。

   なぜ: GA4（日本からの来訪・2026-11-22〜25）で、写真つきの案件のカード（/site-cards.js）のあるトップは押される率が高く、
   文字のリンクだけの市場ノート・コラム・ナレッジの入口はほとんど押されなかった（中島「クリック数とかで戦略を変えていって」）。

   出す頁（header.js の 7g の stripWanted だけが決め、当たる頁でだけ load の後にこの部品を読む）:
     ・市場ノート /research・/research/flash・/research/<YYYY-MM>・/research/data … 常に
     ・ナレッジの入口 /knowledge … 常に
     ・日本語のコラム /column-<slug> … 半分だけ（効き目を比べる）。土地の持ち主向けの4本（land-buyback・land-lease・land-value・land-zoning）は出さない
       分け方の式（Python で同じに再現できる）: sum(ord(ch) for ch in slug) % 2 == 0 の頁に出す（slug＝/column- の後ろ・.html なし）
     ・英語・中国語・トップ・/market-data・入力のフォームの頁には出さない
   出す所: コラムは本文の終わり（関連の記事・よくある質問・近い話題・全体像・監修の欄のうち、h1 より後で一番先に来る物の前）。
           市場ノートは本文の終わり（引用のしかたの段か、下の案内の段の前・無ければ下の帯の前）。ナレッジは書き手の欄の段の前。
   中身: 見出し「いま売りに出ている蓄電所」・カード4枚（写真のある物を先に・口の並びの頭から）・「一覧を見る →」。
         カードの形・欄・言葉はトップ（/site-cards.js の日本語・theme.css の .sc）と同じ。価格は出さない（公開のカードの口は価格を返さない）。
   元: 蓄電所マーケットのログイン前のカードの口 /api/open/cards（site-cards.js と同じ口）。3秒で打ち切り。
       読めない・0枚・形が違う → 何も出さない（枠も見出しも出さない）。
   遅れて読む: 帯の場所が画面の 600px 手前まで来たら（下へ飛んで通り過ぎたときも）口を読み、読めたときだけ差し込む（頁の初めの描画を遅らせない・画面の外で差し込むので本文は跳ねない）。
   印: 帯の入れ物とリンクに data-placement="strip"。header.js が押す直前に ?src=<頁の印>（col-<slug>・report-YYYY-MM・knowledge・site-…）を足し、GA4 の market_click は placement=strip。

   2026-11-25（2）広げた（GA4・日本・直近7日: 表示が多いのにマーケットへ送れていない、帯の無い頁。コラムの半分の比べは変えない）:
     ・会社案内 /company … 「3つの入口」の段のすぐ後（代表メッセージの段の前）に案件の帯
     ・買い手向けの頁 /transfer・/investors・/for/major・/for/sme、読み物の残り /qa・/faq・/glossary … 終わり（下の案内の段の前・無ければ最後の段の前・無ければ下の帯の前）に案件の帯
     ・柱の頁 /guide-<slug> … 本文の終わり（このテーマのコラムの段か、よくある質問の段の前）に案件の帯
     ・売りたい方の頁 /sourcing … 「売り方は2つ」の段のすぐ後に、買主のリクエストの帯（header.js が window.SCIX_STRIP.kind='needs' を渡す）
       中身: 見出し「いま買主が探している蓄電所」・札3枚（口の並びの頭から）・「買主のリクエストをすべて見る →」。
             札は 買主の属性（資本・上場の区分・業種）と、決まった選択肢の行（エリア・電圧・買い方・運転開始・電力の手続き）だけ。価格・社名・自由に書いた文は出さない（口も返さない）。
             「この買主に提案する →」はマーケットの /needs?need=<番号>（ログイン中の売主はそのまま提案の窓・ログイン前は一覧）。
       元: 蓄電所マーケットのログイン前の買主のリクエストの口 /api/open/needs（マーケットの /needs の頁がログイン前に読む口と同じ）。
     ・出さない頁: /grid-storage・/fund・入力のフォームの頁と送信後の頁・/partners・報道の頁・方針の頁・広告の着地の頁・英語・中国語・トップ
   2026-11-25（2b）: 売り案件の市場データ /market-data … 冒頭の段（題と数字の札）のすぐ後に案件の帯。
     プレスリリースの1本目のリンクの着き先で、着いた人は頁の頭を見るので、終わりでなく上に出す（会社案内と同じ考え方）。
   ====================================================== */
(function () {
  'use strict';
  if (window.__scixStrip) return;
  window.__scixStrip = true;
  if (typeof window.fetch !== 'function') return;

  var MARKET = 'https://dealroom.scix.co.jp';
  var SHOW = 4, ASK = 12, TIMEOUT_MS = 3000;
  var KIND = (window.SCIX_STRIP && window.SCIX_STRIP.kind) === 'needs' ? 'needs' : 'deals';   // 帯の種類は header.js の 7g が決める
  var path = window.location.pathname.replace(/\.html$/, '').replace(/\/+$/, '').replace(/\/index$/, '') || '/';

  // トップのカード（site-cards.js の T.ja）と同じ言葉
  var L = {
    pick: 'おすすめ', neu: '新着', photo: '完成時の写真', aerial: '航空写真',
    out: '出力', cap: '容量', run: '運転中', op: '運転', cod: '運転開始', completed: '完工', now: 'いま', procNone: '電力の手続き —',
    seen: function (n) { return '見た人 累計 ' + n + '人'; }, seenT: 'これまでにこの案件のページを開いた方の人数です',
    volt: { '低圧': '低圧', '高圧': '高圧', '特別高圧': '特別高圧' },
    sale: { '完成渡し': '完成渡し', '権利渡し': '権利渡し', '権利譲渡': '権利渡し' },
    steps: { study: '接続検討 回答あり', apply: '発電調整 申込済', deposit: '保証金 支払済', ms: 'MS番号あり', approval: '本回答あり', cost: '負担金 支払済', complete: '完工済み', market: '需給調整参加済み' },
    ym: function (y, m) { return y + '年' + m + '月'; },
    head: 'いま売りに出ている蓄電所', more: '一覧を見る →'
  };
  var ART = { hv: '/img/market/deals.svg', ehv: '/img/market/how.svg', lv: '/img/market/wants.svg' };
  var ID_RX = /^[A-Za-z]{1,6}-\d{1,6}$/;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function voltKey(v) {
    v = String(v || '');
    return v.indexOf('特') >= 0 ? 'ehv' : v.indexOf('低') >= 0 ? 'lv' : v.indexOf('高') >= 0 ? 'hv' : '';
  }
  function voltJa(v) { var k = voltKey(v); return k === 'ehv' ? '特別高圧' : k === 'lv' ? '低圧' : k === 'hv' ? '高圧' : ''; }
  function isNew(since) {
    var s = String(since || '').slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
    var today = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
    var d = (Date.parse(today + 'T00:00:00Z') - Date.parse(s + 'T00:00:00Z')) / 86400e3;
    return d >= 0 && d <= 7;
  }
  function slash(v) {
    var m = String(v || '').match(/^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$/);
    return m ? m[1] + '/' + (+m[2]) + (m[3] ? '/' + (+m[3]) : '') : String(v || '');
  }
  function ymText(v) {
    var m = String(v || '').match(/^(20\d{2})-(\d{2})/);
    return m ? L.ym(m[1], +m[2]) : '';
  }
  function place(c) { return [c.pref, c.muni].filter(Boolean).join(' '); }
  function stepKey(c) { var g = c.gs; return g && g.level >= 0 && g.steps && g.steps[g.level] ? String(g.steps[g.level].key || '') : ''; }
  function hasPhoto(c) { return !c.locked && (c.img === 'cover' || c.img === 'sat'); }

  function gsHtml(c) {
    var g = c.gs, k = stepKey(c);
    if (!g || !g.steps || !g.steps.length || !(g.level >= 0)) return '<div class="sc-gs none"><div class="bar"><i style="width:0"></i></div><span class="now">' + esc(L.procNone) + '</span></div>';
    var pct = Math.round((g.level + 1) / g.steps.length * 100);
    var label = L.steps[k] || g.now || '';
    return '<div class="sc-gs"><div class="bar"><i style="width:' + pct + '%"></i></div><span class="now">' + esc(L.now) + ': <b>' + esc(label) + '</b></span></div>';
  }
  function specHtml(c) {
    var k = stepKey(c), op = c.op || {}, running = k === 'market' || k === 'complete' || op.running;
    var third = '';
    if (running) third = '<div><small>' + esc(L.op) + '</small><b>' + esc(L.run) + '</b>' + (op.ym ? '<span class="sc-cm">' + esc(ymText(op.ym) + ' ' + L.completed) + '</span>' : '') + '</div>';
    else if (op.cod) third = '<div><small>' + esc(L.cod) + '</small><b>' + esc(slash(op.cod)) + '</b></div>';
    var cells = [];
    if (c.mw) cells.push('<div><small>' + esc(L.out) + '</small><b>' + esc(c.mw) + '<i class="u"> MW</i></b></div>');
    if (c.capacityMwh) cells.push('<div><small>' + esc(L.cap) + '</small><b>' + esc(c.capacityMwh) + '<i class="u"> MWh</i></b></div>');
    if (third) cells.push(third);
    return cells.length ? '<div class="sc-spec" style="--n:' + cells.length + '">' + cells.join('') + '</div>' : '';
  }
  function imgHtml(c) {
    var vk = voltKey(c.voltage) || 'hv', real = hasPhoto(c);
    var src = real ? MARKET + '/api/open/photo?id=' + encodeURIComponent(c.id) : ART[vk];
    var alt = real ? (c.img === 'cover' ? L.photo : L.aerial) : '';
    return '<img class="' + (real ? 'ph' : 'art') + '" src="' + esc(src) + '" width="640" height="360" alt="' + esc(alt) + '" loading="lazy" decoding="async" data-art="' + esc(ART[vk]) + '">';
  }
  function cardHtml(c) {
    var vk = voltKey(c.voltage), vname = voltJa(c.voltage);
    var vtag = vk ? '<span class="vtag ' + vk + '">' + esc(L.volt[vname] || vname) + '</span>' : '';
    var sale = c.saleType ? '<span class="atag">' + esc(L.sale[c.saleType] || c.saleType) + '</span>' : '';
    var tl = (c.recommend ? '<span class="sc-rec">' + esc(L.pick) + '</span>' : '') + (isNew(c.firstSeen) ? '<span class="sc-new">' + esc(L.neu) + '</span>' : '');
    var name = c.name || '';
    var href = MARKET + '/deal?id=' + encodeURIComponent(c.id);
    var seen = Number(c.viewersTotal) >= 3 ? '<div class="sc-ft"><span class="seen" title="' + esc(L.seenT) + '">' + esc(L.seen(c.viewersTotal)) + '</span></div>' : '';
    return '<article class="sc" data-id="' + esc(c.id) + '"><div class="sc-img" data-v="' + esc(vk) + '">' + imgHtml(c) + (tl ? '<div class="sc-tl">' + tl + '</div>' : '') + '</div>' +
      '<div class="sc-body"><div class="sc-name" role="heading" aria-level="3" title="' + esc(name) + '"><a class="sc-lk" target="_top" href="' + esc(href) + '" data-placement="strip">' + esc(name) + '</a></div>' +
      '<div class="sc-loc">' + esc(place(c) || '—') + '</div><div class="sc-tags">' + vtag + sale + '</div>' +
      specHtml(c) + gsHtml(c) + seen + '</div></article>';
  }

  // 口の並びの頭から。限定・名前の無い物は使わず、写真のある物を先に（同じ組の中は口の並びのまま）
  function pick(j) {
    if (!j || !Array.isArray(j.cards)) return null;
    var withPh = [], noPh = [];
    for (var i = 0; i < j.cards.length; i++) {
      var c = j.cards[i];
      if (!c || typeof c !== 'object' || c.locked || !ID_RX.test(String(c.id || '')) || !c.name) continue;
      (hasPhoto(c) ? withPh : noPh).push(c);
    }
    var out = withPh.concat(noPh).slice(0, SHOW);
    return out.length ? out : null;
  }

  // ---- 買主のリクエストの帯（kind=needs） ----
  // 言葉はマーケットの /needs の頁と同じ（「この買主に提案する」「相談できる」「会社の概要は確認中」）
  var N = { head: 'いま買主が探している蓄電所', more: '買主のリクエストをすべて見る →', go: 'この買主に提案する →', buyer: '買主', soft: '相談できる', unknown: '会社の概要は確認中' };
  var NEED_KEYS = ['grid_area', 'voltage', 'sale_type', 'cod', 'grid_stage'];   // 出す行＝決まった選択肢の行だけ（ほかの行は口にあっても出さない）
  var NEED_SHOW = 3;
  function whoText(p) {
    p = p && typeof p === 'object' ? p : {};
    var t = [p.capital, p.listed, p.industry].filter(function (v) { return typeof v === 'string' && v; });
    return t.length ? t.join('・').slice(0, 60) : N.unknown;
  }
  // 口の並びの頭から。番号の形が違う物・出せる行が2つ無い物は使わない
  function pickNeeds(j) {
    if (!j || !Array.isArray(j.needs)) return null;
    var out = [];
    for (var i = 0; i < j.needs.length && out.length < NEED_SHOW; i++) {
      var n = j.needs[i];
      if (!n || typeof n !== 'object' || !ID_RX.test(String(n.id || '')) || !Array.isArray(n.rows)) continue;
      var rows = [];
      for (var k = 0; k < NEED_KEYS.length; k++) {
        for (var r = 0; r < n.rows.length; r++) {
          var x = n.rows[r];
          if (x && x.k === NEED_KEYS[k] && typeof x.label === 'string' && x.label && typeof x.value === 'string' && x.value) { rows.push(x); break; }
        }
      }
      if (rows.length < 2) continue;
      out.push({ id: String(n.id), who: whoText(n.profile), rows: rows });
    }
    return out.length ? out : null;
  }
  function needHtml(n) {
    var rows = '';
    for (var i = 0; i < n.rows.length; i++) {
      var r = n.rows[i];
      rows += '<div><dt>' + esc(r.label.slice(0, 20)) + '</dt><dd>' + esc(r.value.slice(0, 80)) + (r.must === 'must' ? '' : ' <span class="mkn-soft">' + esc(N.soft) + '</span>') + '</dd></div>';
    }
    return '<article class="mkn-c" data-id="' + esc(n.id) + '"><div class="mkn-who"><span class="mkn-tag">' + esc(N.buyer) + '</span><b>' + esc(n.who) + '</b></div>' +
      '<dl class="mkn-rows">' + rows + '</dl>' +
      '<a class="mkn-go" target="_top" href="' + esc(MARKET + '/needs?need=' + encodeURIComponent(n.id)) + '" data-placement="strip">' + esc(N.go) + '</a></article>';
  }

  var STYLE = '.mks{container:mks/inline-size;margin:40px 0 32px;padding:0;border:0;background:none}' +
    '.md.mks-wrap .mks,.wrapper.mks-wrap .mks{margin:0}' +
    '.mks-h{margin:0 0 12px;font-size:1.15rem;font-weight:900;line-height:1.4;color:var(--m-ink,#1F2A48);letter-spacing:.01em}' +
    '.mks .mks-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}' +
    '@container mks (min-width:1000px){.mks .mks-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.mks .sc-spec{grid-template-columns:repeat(2,minmax(0,1fr))}.mks .sc-spec>div:last-child:nth-child(odd){grid-column:1/-1}}' +
    '.mks a{border:0!important;box-shadow:none!important;background:none!important}' +
    '.mks .sc-img img{margin:0!important;border:0!important;border-radius:0!important;box-shadow:none!important;max-width:none!important}' +
    '.mks .sc-spec small{display:block;font-size:10.5px;font-weight:700;color:#7A8496!important}' +
    '.mks .sc-name{margin:0!important;padding:0!important;border:0!important}' +
    '.mks .sc-name::before,.mks .sc-name::after{content:none!important}' +
    '.mks .mks-more{margin:14px 0 0!important;padding:0!important;text-align:right;font-size:.95rem;line-height:1.7}' +
    '.mks .mks-more a{color:var(--m-ink,#1F2A48)!important;font-weight:800;text-decoration:underline!important;text-decoration-color:#F59E0B!important;text-decoration-thickness:2px!important;text-underline-offset:3px}' +
    // 段として差す頁（会社案内・買い手向け・売りたい方の頁など）: 前後の段と同じ幅・同じ間
    ':where(.mks-in){max-width:1100px;margin-left:auto;margin-right:auto;padding-left:24px;padding-right:24px;box-sizing:border-box}' +
    'section.mks-sec{padding:28px 0 0!important;margin:0!important;background:none!important;border:0!important}' +
    '.mks-sec .mks{margin:0}' +
    'section.mks-sec.mks-end{padding-bottom:48px!important}' +   // すぐ後が下の帯のとき（下の案内の段が無い頁）
    // 買主のリクエストの札
    '.mkn-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:0}' +
    '.mkn-c{position:relative;display:flex;flex-direction:column;gap:12px;min-width:0;background:#fff;border-radius:18px;border-top:5px solid #F97316;box-shadow:0 4px 16px rgba(31,42,72,.10);padding:16px 18px 18px;transition:box-shadow .15s,transform .15s}' +
    '.mkn-c:hover{box-shadow:0 10px 24px rgba(31,42,72,.16);transform:translateY(-2px)}' +
    '.mkn-who{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:15px;line-height:1.45;color:var(--m-ink,#0B1530)}' +
    '.mkn-who b{font-weight:800;color:var(--m-ink,#0B1530)}' +
    '.mkn-tag{flex:none;font-size:11.5px;font-weight:900;line-height:1.6;color:#B45309;background:#FFF1E3;border-radius:999px;padding:1px 10px}' +
    '.mks .mkn-rows{margin:0!important;padding:0!important;display:block;flex:1;border:0!important;background:none!important}' +
    '.mks .mkn-rows>div{display:grid;grid-template-columns:6.3em minmax(0,1fr);gap:10px;margin:0;padding:7px 0;border:0;border-top:1px solid #EEF1F6;font-size:13.5px;line-height:1.55;background:none}' +
    '.mks .mkn-rows dt{margin:0!important;padding:0!important;font-weight:700;color:#6B7486!important;background:none!important;border:0!important;float:none;width:auto}' +
    '.mks .mkn-rows dd{margin:0!important;padding:0!important;font-weight:700;color:var(--m-ink,#0B1530)!important;background:none!important;border:0!important}' +
    '.mkn-soft{display:inline-block;font-size:11px;font-weight:800;line-height:1.6;color:#8A5A00;background:#FFF4D6;border-radius:999px;padding:0 8px;white-space:nowrap}' +
    '.mks a.mkn-go{display:block;text-align:center;background:var(--m-go,#F97316)!important;color:#fff!important;font-weight:900;font-size:14.5px;line-height:1.4;padding:11px 14px;border-radius:999px;text-decoration:none!important}' +
    '.mks a.mkn-go::after{content:"";position:absolute;inset:0;border-radius:18px}' +
    '.mks a.mkn-go:focus-visible{outline:3px solid #1F2A48;outline-offset:2px}' +
    '@media (max-width:640px){' +
      '.mkn-grid{display:flex;overflow-x:auto;gap:12px;padding:2px 2px 10px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch}' +
      '.mkn-c{flex:0 0 82%;scroll-snap-align:start}' +
      '.mks{margin:32px 0 24px}' +
      '.mks .mks-grid{display:flex;overflow-x:auto;gap:12px;padding:2px 2px 10px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch}' +
      '.mks .sc{flex:0 0 76%;flex-direction:column;scroll-snap-align:start;border-radius:16px}' +
      '.mks .sc-img{flex:none;aspect-ratio:16/9;min-height:0;border-radius:16px 16px 0 0}' +
      '.mks .sc-name{white-space:nowrap;display:block}' +
      '.mks .mks-more{text-align:left}' +
    '}';
  function cssOnce() {
    if (document.getElementById('mks-css')) return;
    var st = document.createElement('style'); st.id = 'mks-css'; st.textContent = STYLE; document.head.appendChild(st);
  }

  // 帯を差す所: { before: 前に差す要素, wrap: 包み方 }。見つからなければ出さない
  function spot() {
    var h1 = document.querySelector('h1');
    function after(el) { return !h1 || !!(h1.compareDocumentPosition(el) & 4); }
    function outside(el) { return !el.closest('header, footer, nav'); }
    if (path.indexOf('/column-') === 0) {
      var cs = document.querySelectorAll('div.related, section[data-scix-faq], aside[data-scix-role], p[data-scix-cluster], div.author-box');
      for (var i = 0; i < cs.length; i++) if (after(cs[i]) && outside(cs[i])) return { before: cs[i], wrap: '' };
      return null;
    }
    if (path === '/knowledge') {
      var ka = document.querySelector('.kh-author'), kw = ka && ka.closest('.wrapper');
      return kw ? { before: kw, wrap: 'wrapper' } : null;
    }
    if (path === '/market-data') {   // 冒頭の段のすぐ後（最初の集計の段の前）。冒頭の段が無ければ、h1 より後の最初の集計の段の前
      var mh = document.querySelector('section.hero'), mn = mh && mh.nextElementSibling;
      if (!mn || !outside(mn) || mn.tagName !== 'SECTION') {
        mn = null;
        var ms = document.querySelectorAll('section.md');
        for (var q = 0; q < ms.length && !mn; q++) if (after(ms[q]) && outside(ms[q])) mn = ms[q];
      }
      return mn && mn.parentNode ? { before: mn, wrap: 'md' } : null;
    }
    // 2026-11-25（2）: 段として差す頁。目印の段が無ければ、下の案内の段 → 最後の段 → 下の帯 の前
    function sec(id) { var el = id && document.getElementById(id); el = el && (el.tagName === 'SECTION' ? el : el.closest('section')); return el && after(el) && outside(el) ? el : null; }
    function tail() {
      var fs = document.querySelectorAll('section.f-sec');
      return document.querySelector('section.cta') || (fs.length ? fs[fs.length - 1] : null) || document.querySelector('footer.scix-footer');
    }
    if (path === '/company' || path === '/sourcing') {
      var t0 = sec(path === '/company' ? 'message' : 'what') || tail();
      return t0 && t0.parentNode ? { before: t0, wrap: 'sec' } : null;
    }
    if (path.indexOf('/guide-') === 0) {
      var gc = sec('cols') || sec('faq');
      return gc ? { before: gc, wrap: '' } : null;
    }
    if (/^\/(?:transfer|investors|qa|faq|glossary|for\/[a-z0-9-]+)$/.test(path)) {
      var t1 = tail();
      return t1 && t1.parentNode ? { before: t1, wrap: 'sec' } : null;
    }
    var cite = document.getElementById('cite'), citeSec = cite && cite.closest('section');
    var t = citeSec || document.querySelector('section.cta') || document.querySelector('footer.scix-footer');
    return t && t.parentNode ? { before: t, wrap: 'md' } : null;
  }

  function build(cards, wrap) {
    var html = '', inner;
    if (KIND === 'needs') {
      for (var k = 0; k < cards.length; k++) html += needHtml(cards[k]);
      inner = '<section class="mks mkn" data-placement="strip" data-nosnippet aria-label="' + esc(N.head) + '">' +
        '<div class="mks-h" role="heading" aria-level="2">' + esc(N.head) + '</div>' +
        '<div class="mkn-grid">' + html + '</div>' +
        '<p class="mks-more"><a target="_top" href="' + MARKET + '/needs" data-placement="strip">' + esc(N.more) + '</a></p></section>';
    } else {
      for (var i = 0; i < cards.length; i++) html += cardHtml(cards[i]);
      inner = '<section class="mks" data-placement="strip" data-nosnippet aria-label="' + esc(L.head) + '">' +
        '<div class="mks-h" role="heading" aria-level="2">' + esc(L.head) + '</div>' +
        '<div class="sc-grid mks-grid">' + html + '</div>' +
        '<p class="mks-more"><a target="_top" href="' + MARKET + '/" data-placement="strip">' + esc(L.more) + '</a></p></section>';
    }
    var box = document.createElement(wrap === 'md' || wrap === 'sec' ? 'section' : 'div');
    if (wrap === 'md') { box.className = 'md mks-wrap'; inner = '<div class="container rp-body">' + inner + '</div>'; }
    else if (wrap === 'sec') { box.className = 'mks-wrap mks-sec'; inner = '<div class="container mks-in">' + inner + '</div>'; }
    else if (wrap === 'wrapper') box.className = 'wrapper mks-wrap';
    else box.className = 'mks-wrap';
    box.setAttribute('data-nosnippet', '');
    box.innerHTML = inner;
    // 写真が読めない（404・限定・巡回の拒否など）ときは、壊れた絵にせず電圧ごとの絵に替える（site-cards.js と同じ）
    box.addEventListener('error', function (e) {
      var t = e.target;
      if (!t || t.tagName !== 'IMG' || !t.classList.contains('ph')) return;
      t.classList.remove('ph'); t.classList.add('art'); t.setAttribute('alt', '');
      t.src = t.getAttribute('data-art') || ART.hv;
    }, true);
    return box;
  }

  function load(slot, wrap) {
    var ctl = typeof AbortController === 'function' ? new AbortController() : null;
    var late = false;
    var timer = setTimeout(function () { late = true; if (ctl) ctl.abort(); }, TIMEOUT_MS);
    var opts = { mode: 'cors', credentials: 'omit', headers: { Accept: 'application/json' } };
    if (ctl) opts.signal = ctl.signal;
    fetch(MARKET + (KIND === 'needs' ? '/api/open/needs?lang=ja' : '/api/open/cards?limit=' + ASK + '&lang=ja'), opts)
      .then(function (r) { clearTimeout(timer); return r.ok ? r.json() : null; })
      .then(function (j) {
        var cards = late ? null : (KIND === 'needs' ? pickNeeds(j) : pick(j));
        if (!cards || !slot.parentNode) { if (slot.parentNode) slot.parentNode.removeChild(slot); return; }
        cssOnce();
        var box = build(cards, wrap);
        // 差す所が画面より上にあり、ブラウザが位置を保たない（overflow-anchor の無い）ときだけ、伸びた分を送って読んでいる所を動かさない
        var above = slot.getBoundingClientRect().top < 0;
        slot.parentNode.replaceChild(box, slot);
        if (wrap === 'sec' && box.nextElementSibling && box.nextElementSibling.tagName === 'FOOTER') box.classList.add('mks-end');
        var anchorOk = !!(window.CSS && window.CSS.supports && window.CSS.supports('overflow-anchor', 'auto'));
        if (above && !anchorOk) window.scrollBy(0, box.getBoundingClientRect().height);
        document.documentElement.setAttribute('data-mks', String(cards.length));
      })
      .catch(function () { clearTimeout(timer); if (slot.parentNode) slot.parentNode.removeChild(slot); /* 読めなければ何も出さない */ });
  }

  function start() {
    var s = spot();
    if (!s) return;
    var slot = document.createElement('div');
    slot.className = 'mks-slot'; slot.setAttribute('aria-hidden', 'true'); slot.style.height = '1px';
    s.before.parentNode.insertBefore(slot, s.before);
    // 帯の場所が画面の下 600px より上に来たら（通り過ぎた・下へ飛んだも含む）読む。送りのたびに1回だけ位置を見る（rAF で間引く）
    var done = false, ticking = false;
    function check() {
      ticking = false;
      if (done || slot.getBoundingClientRect().top > (window.innerHeight || 800) + 600) return;
      done = true;
      window.removeEventListener('scroll', onMove); window.removeEventListener('resize', onMove);
      load(slot, s.wrap);
    }
    function onMove() { if (!ticking) { ticking = true; (window.requestAnimationFrame || setTimeout)(check); } }
    window.addEventListener('scroll', onMove, { passive: true }); window.addEventListener('resize', onMove, { passive: true });
    check();
  }

  try { start(); } catch (e) { /* 帯が無くても頁はそのまま */ }
})();
