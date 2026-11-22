/* ======================================================
   トップの案件カード（日本語・英語・中国語）— 2026-11-22
   コードだけ。案件のデータは持たない（O16-19）。

   HTML には projects.json から焼いた匿名の行（県・電圧・規模まで）が最初から入っている（scripts/inject_stats.py の <!--S:cards-->）。
   この部品は、蓄電所マーケットのログイン前のカードの口（価格のないカードだけを返す）が読めたときだけ、同じ場所を写真つきのカードに差し替える。
   読めない（マーケットが落ちている・遅い・口が閉じている・形が違う）ときは何もしない＝焼いた行のまま残る。
   3秒で打ち切る。写真は枠の大きさを先に取り、遅れて読み込む（枠が跳ねない）。価格の欄は作らない（口が返さない）。
   カードを押すとマーケットの案件へ。ログイン前の人は、マーケットが登録の案内へ回す。
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
      ym: function (y, m) { return y + '年' + m + '月'; }
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
      ym: function (y, m) { return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m - 1] + ' ' + y; }
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
      ym: function (y, m) { return y + '年' + m + '月'; }
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
  }

  // 写真が読めない（404・限定・巡回の拒否など）ときは、壊れた絵にせず電圧ごとの絵に替える
  box.addEventListener('error', function (e) {
    var t = e.target;
    if (!t || t.tagName !== 'IMG' || !t.classList.contains('ph')) return;
    t.classList.remove('ph'); t.classList.add('art');
    t.setAttribute('alt', '');
    t.src = t.getAttribute('data-art') || ART.hv;
  }, true);

  function loadCards() {
    var url = MARKET + '/api/open/cards?limit=' + LIMIT + '&lang=' + dataLang;
    var ctl = typeof AbortController === 'function' ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, TIMEOUT_MS);
    var opts = { mode: 'cors', credentials: 'omit', headers: { Accept: 'application/json' } };
    if (ctl) opts.signal = ctl.signal;
    // AbortController が無い古いブラウザでは、3秒たったら結果を捨てる
    var late = false;
    if (!ctl) setTimeout(function () { late = true; }, TIMEOUT_MS);
    fetch(url, opts)
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
  try { loadNeeds(); } catch (e) { /* 何もしない */ }
})();
