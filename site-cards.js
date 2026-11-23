/* ======================================================
   トップの案件カード（日本語・英語・中国語）— 2026-11-22
   コードだけ。案件のデータは持たない（O16-19）。

   HTML には projects.json から焼いた匿名の行（県・電圧・規模まで）が最初から入っている（scripts/inject_stats.py の <!--S:cards-->）。
   この部品は、蓄電所マーケットのログイン前のカードの口（価格のないカードだけを返す）が読めたときだけ、同じ場所を写真つきのカードに差し替える。
   読めない（マーケットが落ちている・遅い・口が閉じている・形が違う）ときは何もしない＝焼いた行のまま残る。
   3秒で打ち切る。写真は枠の大きさを先に取り、遅れて読み込む（枠が跳ねない）。公開のカードの口は価格を返さない。
   カードを押すとマーケットの案件へ。ログイン前の人は、マーケットが登録の案内へ回す。

   2026-11-23 ログインの持ち越し（中島「サイエンスのTOPに行くとログアウトする仕様はおかしい。ログインしたままにして。」）:
   蓄電所マーケットにログイン中の人（header.js の window.SCIX_MKT_SESSION）だけ、描いたカード（焼いた行も）の id で
   マーケットの口 /api/site/prices（ログインの札で答える・販売中の物の価格の4欄だけ・資格つきの CORS は www.scix.co.jp と scix.co.jp だけ）を読み、価格の段を差し込む。
   前にログインしていた印（html[data-mkt-signed]）がある間は、価格の段を同じ高さの空の仮置きにする（「登録のあと」の字は header.js が隠す）。読めなければ仮置きを外して今の形。
   出し方はマーケットの一覧のカード（public/deal-cards.js の priceHtml）と同じ＝大きい数・税の注・指値歓迎・1kWあたり（別途の手数料は一覧に書かない）。
   ====================================================== */
(function () {
  'use strict';
  var box = document.getElementById('top-cards');
  if (!box) return;

  var MARKET = 'https://dealroom.scix.co.jp';
  var htmlLang = String(document.documentElement.getAttribute('lang') || 'ja').toLowerCase();
  var ui = htmlLang.indexOf('zh') === 0 ? 'zh' : (htmlLang.indexOf('en') === 0 ? 'en' : 'ja');
  var dataLang = ui === 'ja' ? 'ja' : 'en';   // マーケットは日本語と英語だけ。中国語の頁は英語のカードを、中国語の字の枠で出す
  var LIMIT = 12;
  var TIMEOUT_MS = 3000;
  var PRICE_TIMEOUT_MS = 6000;

  var T = {
    ja: {
      pick: 'おすすめ', neu: '新着', locked: '個別にご案内する案件', photo: '完成時の写真', aerial: '航空写真',
      out: '出力', cap: '容量', run: '運転中', op: '運転', cod: '運転開始', completed: '完工', now: 'いま', procNone: '電力の手続き —',
      seen: function (n) { return '見た人 累計 ' + n + '人'; }, seenT: 'これまでにこの案件のページを開いた方の人数です',
      fresh0: '今日、売主に販売中と確かめてあります', freshN: function (n) { return '売主に' + n + '日前に販売中と確かめてあります'; },
      confirmed: function (md) { return '売主確認 ' + md; },
      volt: { '低圧': '低圧', '高圧': '高圧', '特別高圧': '特別高圧' },
      sale: { '完成渡し': '完成渡し', '権利渡し': '権利渡し', '権利譲渡': '権利渡し' },
      steps: { study: '接続検討 回答あり', apply: '発電調整 申込済', deposit: '保証金 支払済', ms: 'MS番号あり', approval: '本回答あり', cost: '負担金 支払済', complete: '完工済み', market: '需給調整参加済み' },
      ym: function (y, m) { return y + '年' + m + '月'; },
      ask: '価格応相談', askSub: '価格は個別にご案内します', nego: '指値歓迎', perKw: function (u) { return u >= 10000 ? '1kWあたり ' + (Math.round(u / 1000) / 10).toLocaleString('ja-JP') + '万円' : '1kWあたり ' + Math.round(u).toLocaleString('ja-JP') + '円'; },
      exTax: '（税抜）', inTax: '（税込）'
    },
    en: {
      pick: 'Our pick', neu: 'New', locked: 'Project shown individually', photo: 'Photo of the completed site', aerial: 'Aerial photo',
      out: 'Output', cap: 'Capacity', run: 'Operating', op: 'Operation', cod: 'COD', completed: 'Completed', now: 'Now', procNone: 'Grid procedure —',
      seen: function (n) { return n + ' viewers so far'; }, seenT: 'People who have opened this project page so far',
      fresh0: 'Seller confirmed on sale today', freshN: function (n) { return 'Seller confirmed on sale ' + n + ' day' + (n === 1 ? '' : 's') + ' ago'; },
      confirmed: function (md) { return 'Seller confirmed ' + md; },
      volt: { '低圧': 'Low voltage', '高圧': 'High voltage', '特別高圧': 'Extra-high voltage' },
      sale: { '完成渡し': 'Sold on completion', '権利渡し': 'Rights transfer', '権利譲渡': 'Rights transfer' },
      steps: { study: 'Connection study answered', apply: 'Generation-adjustment application filed', deposit: 'Deposit paid', ms: 'Application number issued', approval: 'Formal reply received', cost: 'Construction cost paid', complete: 'Completed', market: 'In the balancing market' },
      ym: function (y, m) { return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m - 1] + ' ' + y; },
      ask: 'Price on request', askSub: 'Price given individually', nego: 'Offers invited', perKw: function (u) { return 'JPY ' + Math.round(u).toLocaleString('en-US') + ' / kW'; },
      exTax: 'excl. tax', inTax: 'incl. tax'
    },
    zh: {
      pick: '推荐', neu: '新上架', locked: '个别介绍的项目', photo: '竣工时的照片', aerial: '航拍照片',
      out: '输出功率', cap: '容量', run: '运行中', op: '运行', cod: '预计运行', completed: '竣工', now: '当前', procNone: '电力手续 —',
      seen: function (n) { return '累计 ' + n + ' 人浏览'; }, seenT: '至今打开过该项目页面的人数',
      fresh0: '今天已向卖方确认在售', freshN: function (n) { return n + ' 天前已向卖方确认在售'; },
      confirmed: function (md) { return '卖方确认 ' + md; },
      volt: { '低圧': '低压', '高圧': '高压', '特別高圧': '特别高压' },
      sale: { '完成渡し': '竣工后转让', '権利渡し': '权利转让', '権利譲渡': '权利转让' },
      steps: { study: '已取得接入系统研究答复', apply: '已提交发电调整申请', deposit: '保证金已支付', ms: '已取得受理编号', approval: '已取得正式答复', cost: '并网工程费分摊已支付', complete: '已竣工', market: '已参与调整力市场' },
      ym: function (y, m) { return y + '年' + m + '月'; },
      ask: '价格面议', askSub: '价格个别告知', nego: '可议价', perKw: function (u) { return '每kW ' + (u >= 10000 ? (Math.round(u / 1000) / 10).toLocaleString('zh-CN') + '万日元' : Math.round(u).toLocaleString('zh-CN') + '日元'); },
      exTax: '不含税', inTax: '含税'
    }
  };
  var L = T[ui];

  // 写真が読めないときの絵（電圧ごと。img/market/ に置いてある）
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
  function place(c) {
    if (ui === 'en') return c.placeEn || '';
    return [c.pref, c.muni].filter(Boolean).join(' ') || (ui === 'zh' ? (c.placeEn || '') : '');
  }
  function stepKey(c) { var g = c.gs; return g && g.level >= 0 && g.steps && g.steps[g.level] ? String(g.steps[g.level].key || '') : ''; }

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
    if (running) {
      third = '<div><small>' + esc(L.op) + '</small><b>' + esc(L.run) + '</b>' +
        (op.ym ? '<span class="sc-cm">' + esc(ui === 'en' ? L.completed + ' ' + ymText(op.ym) : ymText(op.ym) + ' ' + L.completed) + '</span>' : '') + '</div>';
    } else if (op.cod) {
      third = '<div><small>' + esc(L.cod) + '</small><b>' + esc(slash(op.cod)) + '</b></div>';
    }
    var cells = [];
    if (c.mw) cells.push('<div><small>' + esc(L.out) + '</small><b>' + esc(c.mw) + '<i class="u"> MW</i></b></div>');
    if (c.capacityMwh) cells.push('<div><small>' + esc(L.cap) + '</small><b>' + esc(c.capacityMwh) + '<i class="u"> MWh</i></b></div>');
    if (third) cells.push(third);
    return cells.length ? '<div class="sc-spec" style="--n:' + cells.length + '">' + cells.join('') + '</div>' : '';
  }
  function ymText(v) {
    var m = String(v || '').match(/^(20\d{2})-(\d{2})/);
    return m ? L.ym(m[1], +m[2]) : '';
  }
  function freshHtml(c) {
    var txt = '';
    if (c.freshDays != null) txt = c.freshDays === 0 ? L.fresh0 : L.freshN(c.freshDays);
    else if (c.confirmedMd) txt = L.confirmed(c.confirmedMd);
    return txt ? '<div class="sc-fresh"><span class="fk" aria-hidden="true">✓</span>' + esc(txt) + '</div>' : '';
  }
  function imgHtml(c, i) {
    var vk = voltKey(c.voltage) || 'hv';
    var real = !c.locked && (c.img === 'cover' || c.img === 'sat');
    var src = real ? MARKET + '/api/open/photo?id=' + encodeURIComponent(c.id) : ART[vk];
    var alt = real ? (c.img === 'cover' ? L.photo : L.aerial) : '';
    return '<img class="' + (real ? 'ph' : 'art') + '" src="' + esc(src) + '" width="640" height="360" alt="' + esc(alt) + '"' +
      (i < 4 ? '' : ' loading="lazy"') + ' decoding="async" data-art="' + esc(ART[vk]) + '">';
  }
  function cardHtml(c, i) {
    var vk = voltKey(c.voltage), vname = voltJa(c.voltage);
    var vtag = vk ? '<span class="vtag ' + vk + '">' + esc(L.volt[vname] || vname) + '</span>' : '';
    var sale = c.saleType ? '<span class="atag">' + esc(L.sale[c.saleType] || c.saleType) + '</span>' : '';
    var tl = (c.recommend ? '<span class="sc-rec">' + esc(L.pick) + '</span>' : '') + (!c.locked && isNew(c.firstSeen) ? '<span class="sc-new">' + esc(L.neu) + '</span>' : '');
    var name = c.locked ? L.locked : (c.name || '');
    var href = MARKET + '/deal?id=' + encodeURIComponent(c.id) + (dataLang === 'en' ? '&lang=en' : '');
    var seen = Number(c.viewersTotal) >= 3 ? '<div class="sc-ft"><span class="seen" title="' + esc(L.seenT) + '">' + esc(L.seen(c.viewersTotal)) + '</span></div>' : '';
    return '<article class="sc" data-id="' + esc(c.id) + '"><div class="sc-img" data-v="' + esc(vk) + '">' + imgHtml(c, i) + (tl ? '<div class="sc-tl">' + tl + '</div>' : '') + '</div>' +
      '<div class="sc-body"><h3 class="sc-name" title="' + esc(name) + '"><a class="sc-lk" href="' + esc(href) + '" data-placement="card">' + esc(name) + '</a></h3>' +
      '<div class="sc-loc">' + esc(place(c) || '—') + '</div><div class="sc-tags">' + vtag + sale + '</div>' +
      freshHtml(c) + specHtml(c) + gsHtml(c) + seen + '</div></article>';
  }

  function valid(j) {
    if (!j || !Array.isArray(j.cards) || !j.cards.length) return null;
    var out = [];
    for (var i = 0; i < j.cards.length && out.length < LIMIT; i++) {
      var c = j.cards[i];
      if (c && typeof c === 'object' && ID_RX.test(String(c.id || ''))) out.push(c);
    }
    return out.length ? out : null;
  }

  function draw(cards) {
    var html = '';
    for (var i = 0; i < cards.length; i++) html += cardHtml(cards[i], i);
    box.innerHTML = html;
    box.setAttribute('data-drawn', '1');
    paintPrices();   // ログイン中（か、その印がある間）は価格の段（か仮置き）を付け直す
  }

  // 写真が読めない（404・限定・巡回の拒否など）ときは、壊れた絵にせず電圧ごとの絵に替える
  box.addEventListener('error', function (e) {
    var t = e.target;
    if (!t || t.tagName !== 'IMG' || !t.classList.contains('ph')) return;
    t.classList.remove('ph'); t.classList.add('art');
    t.setAttribute('alt', '');
    t.src = t.getAttribute('data-art') || ART.hv;
  }, true);

  // ---- ログイン中の人の価格（2026-11-23） ----
  var NEGO_RE = /応相談|ご相談|指値/, NEGO_TXT_RE = /\s*[※・]?\s*(?:価格(?:は)?(?:ご相談に応じます|応相談)|指値(?:歓迎|相談可|可))\s*/, AMOUNT_RX = /^([0-9.,]+\s*億[0-9,]*\s*万?円?|[0-9.,]+\s*万円?|[0-9,]+\s*円)/;
  function money(v) {
    var str = String(v == null ? '' : v), m = str.match(/(\d+(?:\.\d+)?)\s*億\s*([0-9,]+)?\s*万?/);
    if (m) { var y = parseFloat(m[1]) * 1e8; if (m[2]) y += parseInt(m[2].replace(/,/g, ''), 10) * 1e4; return Math.round(y); }
    m = str.match(/([0-9,]+(?:\.\d+)?)\s*万円?/); if (m) return Math.round(parseFloat(m[1].replace(/,/g, '')) * 1e4);
    m = str.match(/([0-9,]{6,})\s*円/); if (m) return parseInt(m[1].replace(/,/g, ''), 10);
    return null;
  }
  function jpy(y) { var m = y / 1e6; return 'JPY ' + (m >= 1 ? m.toLocaleString('en-US', { maximumFractionDigits: 2 }) + ' million' : Math.round(y).toLocaleString('en-US')); }
  function cny(y) { return y >= 1e8 ? (Math.round(y / 1e6) / 100).toLocaleString('zh-CN') + '亿日元' : (Math.round(y / 1e3) / 10).toLocaleString('zh-CN') + '万日元'; }   // 中国語は 亿・万＋日元（英語の JPY を混ぜない）
  /* p＝/api/site/prices の1件 { price, status, mw, maxPower }。日本語はマーケットの字のまま（大きい数と注）、英語・中国語は JPY の数と税の注だけ */
  function priceHtml(p) {
    if (!p) return '';
    var s0 = String(p.price == null ? '' : p.price).trim(), nego = NEGO_RE.test(s0), shown = nego ? s0.replace(NEGO_TXT_RE, '').trim() : s0;
    if (!shown) return '<div class="sc-price"><b class="pn none">' + esc(L.ask) + '</b></div><div class="sc-psub"><span>' + esc(L.askSub) + '</span></div>';
    var m = shown.match(AMOUNT_RX), y = money(shown), big, rest = '';
    var ex = /税抜/.test(shown), inc = /税込/.test(shown) && !ex;
    if (ui === 'ja') { big = m ? m[1] : shown; rest = m ? shown.slice(m[1].length).trim() : ''; }
    else { big = y != null ? (ui === 'zh' ? cny(y) : jpy(y)) : shown; rest = ex ? L.exTax : inc ? L.inTax : ''; }
    // 指値歓迎の札: 日本語は価格の行（短いので収まる）・英語と中国語は下の行（Offers invited が価格の行から落ちてカードの段がずれた＝別の目・2026-11-23）
    var negoTag = nego ? '<span class="nego">' + esc(L.nego) + '</span>' : '';
    var head = '<div class="sc-price" title="' + esc(s0) + '"><b class="pn">' + esc(big) + '</b>' + (rest ? '<span class="ptax">' + esc(rest) + '</span>' : '') +
      (ui === 'ja' ? negoTag : '') + '</div>';
    var kw = Number(p.maxPower), mw = Number(p.mw);
    if (mw > 0 && (!(kw > 0) || Math.abs(kw - mw * 1000) > mw * 50)) kw = mw * 1000;
    var unit = m && y != null && kw > 0 && !/別途必要/.test(shown) ? '<span>' + esc(L.perKw((inc ? y / 1.1 : y) / kw)) + '</span>' : '';
    var low = unit + (ui === 'ja' ? '' : negoTag);
    return head + (low ? '<div class="sc-psub">' + low + '</div>' : '');
  }
  var WAIT = '<div class="sc-price wait" aria-hidden="true"><b class="pn">&nbsp;</b></div><div class="sc-psub wait" aria-hidden="true"><span>&nbsp;</span></div>';
  var PRICES = null;    // 読めた価格（id → 1件）。null＝まだ・読めない
  var PSTATE = document.documentElement.hasAttribute('data-mkt-signed') ? 'guess' : 'anon';   // anon・guess（印だけ）・in（答えでログイン中）
  var PCSS = '#top-cards .sc-price{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 8px;margin:2px 0 0;line-height:1.25}' +
    '#top-cards .sc-price .pn{font-size:20px;font-weight:900;color:#1F2A48;letter-spacing:.01em}' +
    '#top-cards .sc-price .pn.none{font-size:15px;color:#5B667A}' +
    '#top-cards .sc-price .ptax{font-size:11.5px;font-weight:700;color:#5B667A}' +
    '#top-cards .sc-price .nego{font-size:11px;font-weight:800;color:#B45309;background:#FFF4E5;border-radius:999px;padding:1px 8px}' +
    '#top-cards .sc-psub{display:flex;flex-wrap:wrap;align-items:center;gap:2px 8px;margin:-4px 0 0;font-size:12px;font-weight:700;color:#5B667A;line-height:1.4}' +
    '#top-cards .sc-price.wait .pn{display:inline-block;width:9em;border-radius:6px;background:linear-gradient(90deg,#EEF1F7,#F6F8FB,#EEF1F7)}' +
    '#top-cards .sc-psub.wait span{display:inline-block;width:7em;border-radius:6px;background:#F3F5FA}';
  function cssOnce() {
    if (document.getElementById('sc-price-css')) return;
    var st = document.createElement('style'); st.id = 'sc-price-css'; st.textContent = PCSS; document.head.appendChild(st);
  }
  function clearPrices(card) { var olds = card.querySelectorAll('.sc-price, .sc-psub'); for (var i = 0; i < olds.length; i++) olds[i].parentNode.removeChild(olds[i]); }
  function paintPrices() {
    if (PSTATE === 'anon' && !PRICES) { var cs0 = box.querySelectorAll('article.sc'); for (var k = 0; k < cs0.length; k++) clearPrices(cs0[k]); return; }
    cssOnce();
    var cards = box.querySelectorAll('article.sc[data-id]');
    for (var i = 0; i < cards.length; i++) {
      var c = cards[i], id = c.getAttribute('data-id'), tags = c.querySelector('.sc-tags');
      if (!tags) continue;
      var html = PRICES ? priceHtml(PRICES[id]) : WAIT;
      clearPrices(c);
      if (html) tags.insertAdjacentHTML('afterend', html);
    }
  }
  function idsOnCards() {
    var out = [], cards = box.querySelectorAll('article.sc[data-id]');
    for (var i = 0; i < cards.length && out.length < 24; i++) { var id = cards[i].getAttribute('data-id'); if (ID_RX.test(id) && out.indexOf(id) < 0) out.push(id); }
    return out;
  }
  var cardsDone = null;   // 公開のカードの読み込みが終わった（描けた・読めなかった）ら解ける
  function loadPrices() {
    var ids = idsOnCards();
    if (!ids.length) { PSTATE = 'anon'; paintPrices(); return; }
    var ctl = typeof AbortController === 'function' ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, PRICE_TIMEOUT_MS);
    var opts = { mode: 'cors', credentials: 'include', cache: 'no-store' };
    if (ctl) opts.signal = ctl.signal;
    fetch(MARKET + '/api/site/prices?ids=' + encodeURIComponent(ids.join(',')), opts)
      .then(function (r) { clearTimeout(timer); return r.ok ? r.json() : null; })
      .then(function (j) {
        if (j && j.signed === true && j.prices && typeof j.prices === 'object') { PRICES = j.prices; box.setAttribute('data-priced', '1'); }
        else { PSTATE = 'anon'; PRICES = null; }
        paintPrices();
      })
      .catch(function () { clearTimeout(timer); PSTATE = 'anon'; PRICES = null; paintPrices(); });
  }
  function startPrices() {
    if (PSTATE === 'guess') paintPrices();   // 印のある間は、焼いた行にも仮置きの段
    var sp = window.SCIX_MKT_SESSION;
    if (!sp || typeof sp.then !== 'function') { if (PSTATE === 'guess') { PSTATE = 'anon'; paintPrices(); } return; }
    sp.then(function (me) {
      if (!me) { PSTATE = 'anon'; paintPrices(); return; }
      PSTATE = 'in'; paintPrices();
      (cardsDone || Promise.resolve()).then(loadPrices, loadPrices);
    }, function () { PSTATE = 'anon'; paintPrices(); });
  }

  function loadCards() {
    var url = MARKET + '/api/open/cards?limit=' + LIMIT + '&lang=' + dataLang;
    var ctl = typeof AbortController === 'function' ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, TIMEOUT_MS);
    var opts = { mode: 'cors', credentials: 'omit', headers: { Accept: 'application/json' } };
    if (ctl) opts.signal = ctl.signal;
    // AbortController が無い古いブラウザでは、3秒たったら結果を捨てる
    var late = false;
    if (!ctl) setTimeout(function () { late = true; }, TIMEOUT_MS);
    cardsDone = fetch(url, opts)
      .then(function (r) { clearTimeout(timer); return r.ok ? r.json() : null; })
      .then(function (j) { var cards = late ? null : valid(j); if (cards) draw(cards); })
      .catch(function () { clearTimeout(timer); /* 読めなければ焼いた行のまま */ });
  }

  // 買主のリクエストの件数（売りたい方の一行）。マーケットの公開の口から読む＝公開してよい項目だけ
  function loadNeeds() {
    var els = document.querySelectorAll('[data-mk="needs"]');
    if (!els.length) return;
    fetch(MARKET + '/api/open/needs', { mode: 'cors', credentials: 'omit' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        var n = j && Array.isArray(j.needs) ? j.needs.length : 0;
        if (!n) return;
        var txt = ui === 'en' ? ' (' + n + ')' : ui === 'zh' ? '（' + n + '条）' : '（' + n + '件）';
        for (var i = 0; i < els.length; i++) els[i].textContent = txt;
      })
      .catch(function () { /* 読めなければ件数は出さない */ });
  }

  try { loadCards(); } catch (e) { /* 何もしない */ }
  try { startPrices(); } catch (e) { /* 価格は出さない（今の形） */ }
  try { loadNeeds(); } catch (e) { /* 何もしない */ }
})();
