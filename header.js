(function () {
  /* ======================================================
     ScienceX — Shared Navigation Header (JP + EN + 简中)
     Single source of truth for all pages.

     2026-09-17: JP nav regrouped by the visitor's position —
       買う ▾ / 売る ▾ / 学ぶ ▾ / 会社案内 / お問い合わせ / gold CTA.
       (Was: 9 flat items + 1 dropdown + 3 language pills = 16 targets.)
       The language switcher now lives inside the nav: quiet text on
       desktop, bottom row of the drawer on mobile. On mobile the three
       groups are accordions (closed unless it holds the current page).
       GA4: nav_click / nav_open events so the change can be measured.
     ====================================================== */

  // --------------- 0. Language detection ---------------
  var path = window.location.pathname
    .replace(/\.html$/, '')
    .replace(/\/+$/, '') || '/';
  var isEn = path === '/en' || path.indexOf('/en/') === 0;
  var isZh = path === '/zh' || path.indexOf('/zh/') === 0 || path.indexOf('/zh-') === 0;
  var isJa = !isEn && !isZh;
  var prefix = isEn ? '/en' : '';
  // trailingSlash is false, so '/en/' would cost a 308 on every EN page.
  var logoHref = isZh ? '/zh' : (isEn ? '/en' : '/');

  // Canonical page id, shared across languages.
  // JP is the superset; EN/ZH are single-funnel subsets.
  var loc;
  if (isEn) {
    loc = path.replace(/^\/en/, '') || '/';
    if (loc === '/market-entry') loc = '/market-entry-guide';
  } else if (isZh) {
    if (path === '/zh') loc = '/';
    else if (path === '/zh-knowledge') loc = '/knowledge';
    else if (path === '/zh-qa') loc = '/qa';
    else if (path === '/zh-contact') loc = '/contact';
    else if (path === '/zh-thanks') loc = '/thanks';
    else if (path === '/zh-primer') loc = '/primer';
    else if (path.indexOf('/zh-column-') === 0) loc = '/column-' + path.slice('/zh-column-'.length);
    else loc = '/';
  } else {
    loc = path;
  }
  var isCol = loc.indexOf('/column-') === 0;

  // Columns that exist in Japanese only. Switching language from these must
  // fall back to the knowledge hub instead of a URL that does not exist.
  var JA_ONLY_COLUMNS = [
    '/column-capacity-market',
    '/column-day-ahead',
    '/column-investment-tax-law',
    '/column-investment-tax-practice',
    '/column-investment-tax-schedule',
    '/column-jcstar-levels',
    '/column-land-buyback',
    '/column-land-lease',
    '/column-land-zoning'
  ];
  // Pages with no Japanese counterpart. /grid-storage is the closest JA page
  // (it is the "what is grid-scale storage" explainer these two translate).
  var NO_JA_PAGE = { '/primer': '/grid-storage', '/market-entry-guide': '/grid-storage' };
  // Pages that exist in all three languages under language-specific slugs.
  var TRILINGUAL = {
    '/': { en: '/en', zh: '/zh' },
    '/knowledge': { en: '/en/knowledge', zh: '/zh-knowledge' },
    '/qa': { en: '/en/qa', zh: '/zh-qa' },
    '/contact': { en: '/en/contact', zh: '/zh-contact' },
    '/thanks': { en: '/en/thanks', zh: '/zh-thanks' },
    '/primer': { en: '/en/primer', zh: '/zh-primer' },
    '/market-entry-guide': { en: '/en/market-entry-guide', zh: '/zh' }
  };

  // Below this width the nav collapses into the drawer. The regrouped nav is
  // short enough that an iPad in landscape (1024px) keeps the full bar.
  var BP = 900;

  // --------------- 1. CSS ---------------
  var css = [
    '/* === ScienceX Header Reset === */',
    '.scix-header,.scix-header *,.scix-header *::before,.scix-header *::after{margin:0;padding:0;box-sizing:border-box}',

    '/* === Body offset for fixed header === */',
    'body{padding-top:64px!important}',

    '/* === Header bar === */',
    '.scix-header{',
    '  position:fixed;top:0;left:0;right:0;height:64px;',
    '  background:#1B2A4A;',
    '  z-index:9999;',
    '  border-bottom:1px solid rgba(196,154,60,.25);',
    '  font-family:"Noto Sans JP",sans-serif;',
    '}',

    '.scix-header-inner{',
    '  max-width:1100px;margin:0 auto;height:100%;',
    '  display:flex;align-items:center;justify-content:space-between;',
    '  padding:0 24px;',
    '}',

    '/* === Logo === */',
    '.scix-header-logo{',
    '  text-decoration:none;display:flex;align-items:center;flex-shrink:0;',
    '}',
    '.scix-header-logo img{',
    '  height:36px;width:auto;display:block;',
    '}',

    '/* === Desktop nav === */',
    '.scix-header-nav{',
    '  display:flex;align-items:center;gap:2px;',
    '}',
    '.scix-header-nav a,.scix-nav-dd-toggle{',
    '  text-decoration:none;color:rgba(255,255,255,.78);',
    '  font-size:.84rem;font-weight:400;letter-spacing:.1px;line-height:1.4;',
    '  padding:8px 11px;border-radius:4px;',
    '  background:none;border:none;cursor:pointer;font-family:inherit;',
    '  transition:color .25s,background .25s;',
    '  white-space:nowrap;',
    '}',
    '.scix-header-nav a:hover,.scix-nav-dd-toggle:hover{color:#fff;background:rgba(255,255,255,.08)}',
    '.scix-header-nav a.active,.scix-nav-dd-toggle.active{color:#fff;font-weight:600;background:rgba(255,255,255,.12)}',
    '.scix-header-nav a:focus-visible,.scix-nav-dd-toggle:focus-visible{outline:2px solid #E4C871;outline-offset:2px}',

    '/* === Primary CTA button (gold) === */',
    '.scix-header-nav a.scix-cta{',
    '  background:#D2B65F;color:#16223C;font-weight:700;letter-spacing:.2px;',
    '  padding:9px 20px;border-radius:5px;margin-left:14px;',
    '  box-shadow:0 4px 14px rgba(210,182,95,.45);',
    '}',
    '.scix-header-nav a.scix-cta:hover{background:#E4C871;box-shadow:0 6px 18px rgba(210,182,95,.6);transform:translateY(-1px)}',
    '.scix-header-nav a.scix-cta.active{background:#E4C871;color:#16223C}',

    '/* === Dropdown groups (買う / 売る / 学ぶ) === */',
    '.scix-nav-dd{position:relative;display:flex;align-items:center;}',
    '.scix-nav-dd-toggle{display:inline-flex;align-items:center;gap:5px;}',
    '.scix-dd-caret{font-size:.7em;transition:transform .25s;opacity:.85}',
    '.scix-nav-dd-menu{',
    '  position:absolute;top:100%;left:0;min-width:224px;',
    '  background:#1B2A4A;border:1px solid rgba(196,154,60,.28);border-radius:8px;',
    '  padding:6px;display:none;flex-direction:column;gap:2px;',
    '  box-shadow:0 14px 30px rgba(0,0,0,.30);z-index:10003;',
    '}',
    '.scix-nav-dd.open .scix-nav-dd-menu{display:flex}',
    '.scix-nav-dd.open .scix-dd-caret{transform:rotate(180deg)}',
    '/* hover-open only where a real pointer exists (not iPad / touch laptops in the wide layout) */',
    '@media(hover:hover){',
    '  .scix-nav-dd:hover .scix-nav-dd-menu{display:flex}',
    '  .scix-nav-dd:hover .scix-dd-caret{transform:rotate(180deg)}',
    '}',
    '.scix-nav-dd-menu a{padding:10px 12px;border-radius:4px;}',

    '/* === Language switcher (inside the nav) === */',
    '.scix-lang{',
    '  display:flex;align-items:center;gap:0;flex-shrink:0;',
    '  margin-left:12px;padding-left:12px;border-left:1px solid rgba(255,255,255,.18);',
    '}',
    '.scix-header-nav .scix-lang a{font-size:.72rem;color:rgba(255,255,255,.55);padding:6px 7px;letter-spacing:.3px}',
    '.scix-header-nav .scix-lang a:hover{color:#fff;background:rgba(255,255,255,.08)}',
    '.scix-header-nav .scix-lang a.active{color:#fff;font-weight:600;background:none}',

    '/* === Hamburger button (mobile only) === */',
    '.scix-header-burger{',
    '  display:none;background:none;border:none;cursor:pointer;',
    '  width:28px;height:20px;position:relative;z-index:10002;',
    '  flex-shrink:0;',
    '}',
    '.scix-header-burger span{',
    '  display:block;position:absolute;left:0;width:100%;height:2px;',
    '  background:#fff;border-radius:1px;',
    '  transition:transform .3s,opacity .3s;',
    '}',
    '.scix-header-burger span:nth-child(1){top:0}',
    '.scix-header-burger span:nth-child(2){top:9px}',
    '.scix-header-burger span:nth-child(3){top:18px}',

    '/* Burger → X animation */',
    '.scix-header-open .scix-header-burger span:nth-child(1){transform:translateY(9px) rotate(45deg)}',
    '.scix-header-open .scix-header-burger span:nth-child(2){opacity:0}',
    '.scix-header-open .scix-header-burger span:nth-child(3){transform:translateY(-9px) rotate(-45deg)}',

    '/* === Overlay backdrop (mobile) === */',
    '.scix-header-overlay{',
    '  display:none;position:fixed;top:0;left:0;right:0;bottom:0;',
    '  background:rgba(0,0,0,.5);z-index:9997;',
    '  opacity:0;transition:opacity .3s;',
    '}',
    '.scix-header-open .scix-header-overlay{display:block;opacity:1}',

    '/* === Mobile / narrow breakpoint (drawer) === */',
    '@media(max-width:' + BP + 'px){',
    '  .scix-header-nav{',
    '    position:fixed;top:0;right:0;bottom:0;',
    '    width:300px;max-width:84vw;',
    '    background:#1B2A4A;',
    '    flex-direction:column;align-items:stretch;gap:0;',
    '    padding:76px 20px 32px;',
    '    transform:translateX(100%);',
    '    transition:transform .35s cubic-bezier(.4,0,.2,1);',
    '    z-index:10001;',
    '    box-shadow:-4px 0 24px rgba(0,0,0,.15);',
    '    overflow-y:auto;',
    '  }',
    '  .scix-header-open .scix-header-nav{transform:translateX(0)}',
    '  .scix-header-nav a,.scix-nav-dd-toggle{',
    '    padding:14px 12px;font-size:.95rem;',
    '    border-bottom:1px solid rgba(255,255,255,.08);',
    '    border-radius:0;',
    '  }',
    '  .scix-header-nav a.scix-cta{',
    '    margin:18px 0 0;text-align:center;',
    '    border-radius:4px;border-bottom:none;',
    '    padding:14px 20px;',
    '  }',
    '  .scix-nav-dd{flex-direction:column;align-items:stretch;}',
    '  .scix-nav-dd-toggle{justify-content:space-between;width:100%;text-align:left;}',
    '  .scix-nav-dd-toggle.active{background:none;}',
    '  .scix-nav-dd-menu{position:static;display:none;border:none;box-shadow:none;background:rgba(255,255,255,.04);padding:2px 0;min-width:0;border-radius:0;}',
    '  .scix-nav-dd:hover:not(.open) .scix-nav-dd-menu{display:none}',
    '  .scix-nav-dd:hover:not(.open) .scix-dd-caret{transform:none}',
    '  .scix-nav-dd.open .scix-nav-dd-menu{display:flex}',
    '  .scix-nav-dd.open .scix-dd-caret{transform:rotate(180deg)}',
    '  .scix-nav-dd-menu a{padding:12px 12px 12px 28px;font-size:.88rem;border-bottom:1px solid rgba(255,255,255,.06);border-radius:0;}',
    '  .scix-nav-dd-menu a:last-child{border-bottom:none}',
    '  .scix-lang{margin:22px 0 0;padding:0;border-left:none;justify-content:center;gap:6px;}',
    '  .scix-header-nav .scix-lang a{font-size:.85rem;padding:8px 14px;border-bottom:none;border-radius:16px;}',
    '  .scix-header-nav .scix-lang a.active{background:rgba(255,255,255,.14)}',
    '  .scix-header-burger{display:block}',
    '}'
  ].join('\n');

  // Floating mobile contact CTA — on mobile the nav collapses into the hamburger,
  // so keep a persistent, always-visible conversion path. navy-on-gold = WCAG AA.
  css += "\n.scix-float-cta{position:fixed;right:16px;bottom:16px;z-index:9000;display:none;align-items:center;gap:7px;padding:13px 20px;background:#C49A3C;color:#1B2A4A;font-family:'Noto Sans JP',sans-serif;font-size:14px;font-weight:700;text-decoration:none;border-radius:100px;box-shadow:0 6px 20px rgba(27,42,74,.28)}.scix-float-cta:active{transform:translateY(1px)}.scix-float-cta svg{width:16px;height:16px}@media(max-width:768px){.scix-float-cta{display:inline-flex}}";

  var style = document.createElement('style');
  style.id = 'scix-header-css';
  style.textContent = css;
  document.head.appendChild(style);

  // --------------- 2. HTML (language-aware) ---------------
  // JP = three-sided marketplace, grouped by what the visitor came to do:
  //   買う (buy a project / how buying works / hold via the fund)
  //   売る (sell a project or its rights / sell or lease land / introduce)
  //   学ぶ (how the business works / beginner Q&A / knowledge columns)
  // EN & 简中 = single inbound funnel for foreign capital → Home / Knowledge / Contact only.
  function ddGroup(key, label, items) {
    var out = '<div class="scix-nav-dd" data-group="' + key + '">' +
      '<button type="button" class="scix-nav-dd-toggle" aria-expanded="false" aria-controls="scix-dd-' + key + '">' +
        label + '<span class="scix-dd-caret" aria-hidden="true">▾</span>' +
      '</button>' +
      '<div class="scix-nav-dd-menu" id="scix-dd-' + key + '">';
    for (var i = 0; i < items.length; i++) {
      out += '<a href="' + items[i][0] + '" data-page="' + items[i][0] + '">' + items[i][1] + '</a>';
    }
    return out + '</div></div>';
  }

  // Pages that light up each group (beyond the links listed inside it).
  var GROUP_PAGES = {
    buy:   ['/projects', '/transfer', '/fund', '/investors'],
    sell:  ['/sourcing', '/sourcing-criteria', '/land', '/partners', '/sell-form'],
    learn: ['/grid-storage', '/qa', '/knowledge']
  };

  var nav = isZh ? [
    '<a href="/zh"           data-page="/">首页</a>',
    '<a href="/zh-knowledge" data-page="/knowledge">洞见</a>',
    '<a href="/zh-qa"        data-page="/qa">问答</a>',
    '<a href="/zh-contact" class="scix-cta">联系我们</a>'
  ] : isEn ? [
    '<a href="/en"           data-page="/">Home</a>',
    '<a href="/en/knowledge" data-page="/knowledge">Knowledge</a>',
    '<a href="/en/qa"        data-page="/qa">Q&amp;A</a>',
    '<a href="/en/market-entry-guide" data-page="/market-entry-guide">Market Entry Guide</a>',
    '<a href="/en/contact" class="scix-cta">Contact</a>'
  ] : [
    ddGroup('buy', '買う', [
      ['/projects', '販売中の案件一覧'],
      ['/transfer', '買うまでの流れ'],
      ['/fund',     'ファンドで持つ']
    ]),
    ddGroup('sell', '売る', [
      ['/sourcing', '案件・権利を売る'],
      ['/land',     '土地を売る・貸す'],
      ['/partners', '案件・投資家を紹介する']
    ]),
    ddGroup('learn', '学ぶ', [
      ['/grid-storage', '蓄電池事業のしくみ'],
      ['/qa',           '入門Q&amp;A'],
      ['/knowledge',    'ナレッジ（コラム一覧）']
    ]),
    '<a href="/company"  data-page="/company">会社案内</a>',
    '<a href="/contact"  data-page="/contact">お問い合わせ</a>',
    '<a href="/projects" data-page="/projects" class="scix-cta">販売中の案件を見る</a>'
  ];

  // --------------- Language switcher (JA / EN / 简中) ---------------
  // Targets resolve to the equivalent page where it exists, otherwise the
  // closest page in that language — never a 404, never a link to itself.
  var jaOnlyColumn = isCol && JA_ONLY_COLUMNS.indexOf(loc) !== -1;

  var jpHref;
  if (isJa) jpHref = path;
  else if (NO_JA_PAGE[loc]) jpHref = NO_JA_PAGE[loc];
  else if (isCol) jpHref = loc;
  else if (TRILINGUAL[loc]) jpHref = loc;
  else jpHref = '/';

  var enHref;
  if (isEn) enHref = path;
  else if (isCol) enHref = jaOnlyColumn ? '/en/knowledge' : ('/en' + loc);
  else if (TRILINGUAL[loc]) enHref = TRILINGUAL[loc].en;
  else enHref = '/en';

  var zhHref;
  if (isZh) zhHref = path;
  else if (isCol) zhHref = jaOnlyColumn ? '/zh-knowledge' : ('/zh-column-' + loc.slice('/column-'.length));
  else if (TRILINGUAL[loc]) zhHref = TRILINGUAL[loc].zh;
  else zhHref = '/zh';

  var langSwitch = [
    '<div class="scix-lang" role="group" aria-label="' + (isEn ? 'Language' : (isZh ? '语言' : '言語')) + '">',
    '  <a href="' + jpHref + '" hreflang="ja" lang="ja"' + (isJa ? ' class="active" aria-current="true"' : '') + '>JP</a>',
    '  <a href="' + enHref + '" hreflang="en" lang="en"' + (isEn ? ' class="active" aria-current="true"' : '') + '>EN</a>',
    '  <a href="' + zhHref + '" hreflang="zh" lang="zh"' + (isZh ? ' class="active" aria-current="true"' : '') + '>简中</a>',
    '</div>'
  ].join('\n');

  var burgerLabel = isEn ? 'Open menu' : (isZh ? '开启菜单' : 'メニューを開く');
  var navLabel = isEn ? 'Main navigation' : (isZh ? '主导航' : 'メインナビゲーション');

  var header = document.createElement('header');
  header.className = 'scix-header';
  header.id = 'scix-header';
  header.innerHTML = [
    '<div class="scix-header-overlay" id="scix-header-overlay"></div>',
    '<div class="scix-header-inner">',
    '  <a href="' + logoHref + '" class="scix-header-logo"><img src="/img/logo-white.png" alt="ScienceX" width="91" height="36" decoding="async"></a>',
    '  <nav class="scix-header-nav" id="scix-header-nav" aria-label="' + navLabel + '">',
         nav.join('\n'),
         langSwitch,
    '  </nav>',
    '  <button class="scix-header-burger" id="scix-header-burger" aria-label="' + burgerLabel + '" aria-expanded="false" aria-controls="scix-header-nav">',
    '    <span></span><span></span><span></span>',
    '  </button>',
    '</div>'
  ].join('\n');

  document.body.insertBefore(header, document.body.firstChild);

  // Floating contact CTA (mobile only; hidden on the contact/sell-form/thanks pages themselves)
  if (!/contact|sell-form|thanks/.test(path)) {
    var isLandPage = ['/land', '/column-land-buyback', '/column-land-value', '/column-noise'].indexOf(path) !== -1;
    var fcta = document.createElement('a');
    fcta.className = 'scix-float-cta';
    fcta.href = isLandPage ? '/sell-form?type=land' : (isZh ? '/zh-contact' : (isEn ? '/en/contact' : '/contact'));
    fcta.setAttribute('target', '_top');
    fcta.setAttribute('aria-label', isLandPage ? '無料で用地査定' : (isEn ? 'Contact us' : (isZh ? '咨询' : 'ご相談・お問い合わせ')));
    fcta.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>' + (isLandPage ? '無料で用地査定' : (isEn ? 'Contact' : (isZh ? '咨询' : '相談する')));
    document.body.appendChild(fcta);
  }

  // --------------- 3. Active page detection ---------------
  var links = header.querySelectorAll('.scix-header-nav a');
  for (var i = 0; i < links.length; i++) {
    var page = links[i].getAttribute('data-page');
    if (!page) continue;
    if (loc === page) {
      links[i].classList.add('active');
    }
    if (page === '/' && (loc === '' || loc === '/index')) {
      links[i].classList.add('active');
    }
    if (page === '/knowledge' && isCol) {
      links[i].classList.add('active');
    }
  }

  // --------------- 3b. Dropdown groups (買う / 売る / 学ぶ) ---------------
  function isNarrowNow() {
    return !!(window.matchMedia && window.matchMedia('(max-width:' + BP + 'px)').matches);
  }
  var isNarrow = isNarrowNow();
  var dds = header.querySelectorAll('.scix-nav-dd');

  function setOpen(dd, open) {
    dd.classList.toggle('open', open);
    var t = dd.querySelector('.scix-nav-dd-toggle');
    if (t) t.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function closeAllDropdowns(except) {
    for (var k = 0; k < dds.length; k++) {
      if (dds[k] !== except) setOpen(dds[k], false);
    }
  }

  for (var d = 0; d < dds.length; d++) {
    (function (dd) {
      var key = dd.getAttribute('data-group');
      var toggle = dd.querySelector('.scix-nav-dd-toggle');
      var pages = GROUP_PAGES[key] || [];
      var holdsCurrent = pages.indexOf(loc) !== -1 || (key === 'learn' && isCol);
      if (holdsCurrent) {
        toggle.classList.add('active');
        // In the drawer, start with the visitor's own group unfolded.
        if (isNarrow) setOpen(dd, true);
      }
      // Click/tap toggle (touch + keyboard; desktop also opens on hover via CSS).
      toggle.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var willOpen = !dd.classList.contains('open');
        closeAllDropdowns(dd);
        setOpen(dd, willOpen);
        if (willOpen && typeof window.gtag === 'function') {
          try {
            window.gtag('event', 'nav_open', {
              nav_group: key,
              open_by: 'click',
              page_lang: (document.documentElement.lang || 'ja'),
              transport_type: 'beacon'
            });
          } catch (err) { /* ignore */ }
        }
      });
      // Keyboard: ArrowDown opens the group and moves focus to its first link;
      // Enter / Space keep the native button click. Focus leaving the group
      // (Tab past the last link) closes it so no menu is left hanging open.
      toggle.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowDown') return;
        e.preventDefault();
        closeAllDropdowns(dd);
        setOpen(dd, true);
        var first = dd.querySelector('.scix-nav-dd-menu a');
        if (first) first.focus();
      });
      var hoverCounted = false;
      dd.addEventListener('mouseenter', function () {
        if (hoverCounted || isNarrowNow() || typeof window.gtag !== 'function') return;
        if (!(window.matchMedia && window.matchMedia('(hover:hover)').matches)) return;
        hoverCounted = true;
        try {
          window.gtag('event', 'nav_open', {
            nav_group: key,
            open_by: 'hover',
            page_lang: (document.documentElement.lang || 'ja'),
            transport_type: 'beacon'
          });
        } catch (err) { /* ignore */ }
      });
      dd.addEventListener('focusout', function (e) {
        if (isNarrowNow()) return;
        var to = e.relatedTarget;
        if (!to || !dd.contains(to)) setOpen(dd, false);
      });
    })(dds[d]);
  }
  // Close on outside click (desktop only — in the drawer the groups are
  // accordions and must survive taps on the burger / other rows).
  document.addEventListener('click', function (e) {
    if (isNarrowNow()) return;
    var inside = false;
    for (var k = 0; k < dds.length; k++) {
      if (dds[k].contains(e.target)) { inside = true; break; }
    }
    if (!inside) closeAllDropdowns(null);
  });

  // --------------- 4. Hamburger toggle ---------------
  var burger = document.getElementById('scix-header-burger');
  var overlay = document.getElementById('scix-header-overlay');
  var openLabel = burgerLabel;
  var closeLabel = isEn ? 'Close menu' : (isZh ? '关闭菜单' : 'メニューを閉じる');

  function toggleMenu() {
    var isOpen = header.classList.toggle('scix-header-open');
    document.body.style.overflow = isOpen ? 'hidden' : '';
    burger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    burger.setAttribute('aria-label', isOpen ? closeLabel : openLabel);
    syncInert();
    if (isOpen && typeof window.gtag === 'function') {
      try {
        window.gtag('event', 'nav_open', {
          nav_group: 'drawer',
          open_by: 'click',
          page_lang: (document.documentElement.lang || 'ja'),
          transport_type: 'beacon'
        });
      } catch (err) { /* ignore */ }
    }
  }

  function closeMenu() {
    header.classList.remove('scix-header-open');
    document.body.style.overflow = '';
    burger.setAttribute('aria-expanded', 'false');
    burger.setAttribute('aria-label', openLabel);
    syncInert();
  }

  // Keep the closed drawer out of the tab order / a11y tree on narrow screens.
  var navEl = document.getElementById('scix-header-nav');
  function syncInert() {
    var hide = isNarrowNow() && !header.classList.contains('scix-header-open');
    if (hide) navEl.setAttribute('inert', ''); else navEl.removeAttribute('inert');
  }
  syncInert();
  if (window.matchMedia) {
    var mq = window.matchMedia('(max-width:' + BP + 'px)');
    if (mq.addEventListener) mq.addEventListener('change', syncInert);
    else if (mq.addListener) mq.addListener(syncInert);
  }

  burger.addEventListener('click', toggleMenu);
  overlay.addEventListener('click', closeMenu);

  for (var j = 0; j < links.length; j++) {
    links[j].addEventListener('click', closeMenu);
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var focused = document.activeElement;
    for (var k = 0; k < dds.length; k++) {
      if (dds[k].classList.contains('open') && focused && dds[k].contains(focused)) {
        var tg = dds[k].querySelector('.scix-nav-dd-toggle');
        if (tg) tg.focus();
      }
    }
    closeAllDropdowns(null);
    if (header.classList.contains('scix-header-open')) {
      closeMenu();
      burger.focus();
    }
  });

  // --------------- 5. tel: / mailto: クリック計測 (全ページ共通・GA4) ---------------
  // header.js は全ページで読み込まれるため、ここに置けば言語・ページを問わず
  // 電話・メールのクリックを contact_click として1か所で計測できる。
  document.addEventListener('click', function (e) {
    var t = e.target;
    var a = t && t.closest ? t.closest('a[href^="tel:"],a[href^="mailto:"]') : null;
    if (!a || typeof window.gtag !== 'function') return;
    var href = a.getAttribute('href') || '';
    var method = href.indexOf('tel:') === 0 ? 'tel' : 'mailto';
    try {
      window.gtag('event', 'contact_click', {
        method: method,
        link_url: href,
        page_lang: (document.documentElement.lang || 'ja'),
        transport_type: 'beacon'
      });
    } catch (err) { /* ignore */ }
  }, true);

  // --------------- 5b. ヘッダー内リンクのクリック計測 (nav_click・GA4) ---------------
  // 2026-09-17 のナビ再編の効果を測るための計測。nav_group は
  // buy / sell / learn（引き出しの中）・top（会社案内・お問い合わせ）・cta（金ボタン）・
  // lang（言語切替）・logo のいずれか。
  header.addEventListener('click', function (e) {
    var t = e.target;
    var a = t && t.closest ? t.closest('.scix-header-nav a, .scix-header-logo') : null;
    if (!a || typeof window.gtag !== 'function') return;
    var group;
    if (a.classList.contains('scix-header-logo')) group = 'logo';
    else if (a.classList.contains('scix-cta')) group = 'cta';
    else if (a.closest('.scix-lang')) group = 'lang';
    else if (a.closest('.scix-nav-dd')) group = a.closest('.scix-nav-dd').getAttribute('data-group') || 'group';
    else group = 'top';
    try {
      window.gtag('event', 'nav_click', {
        nav_group: group,
        link_text: ((a.textContent || '').replace(/\s+/g, ' ').trim() || (a.querySelector('img') ? a.querySelector('img').getAttribute('alt') : '') || '').slice(0, 40),
        link_url: a.getAttribute('href') || '',
        page_lang: (document.documentElement.lang || 'ja'),
        transport_type: 'beacon'
      });
    } catch (err) { /* ignore */ }
  }, true);

  // --------------- 6. 面談の予約について ---------------
  // 2026-09-05 撤去。Googleカレンダーの「予約スケジュール」は Google Meet のリンクを発行するため、
  // 「こちらが主催する会議は必ず Zoom」（2026-08-23 決定）に反する。
  // 面談は問い合わせへの返信で候補日時を出して決める。各ページの予約ボタンも同時に削除した。
  // 復活させるときは Zoom 側の予約ページを用意してからにする。

})();
