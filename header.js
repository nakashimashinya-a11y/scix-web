(function () {
  /* ======================================================
     ScienceX — Shared Navigation Header (JP + EN + 简中)
     Single source of truth for all pages.

     2026-09-17 (2): ナレッジ moved to the first slot as its own two-column
       menu (テーマで読む / はじめての方). GA4 shows /knowledge is the #1
       next click from the top page and from column pages, and the #2 most
       viewed page — it was buried as the 3rd item of 学ぶ ▾.
       ナレッジ ▾ / 買う ▾ / 売る ▾ / 会社案内 / お問い合わせ / gold CTA.
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

    '/* === Dropdown groups (ナレッジ / 買う / 売る) === */',
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
    '/* two-column menu (ナレッジ): テーマで読む | はじめての方 */',
    '.scix-nav-dd-menu.scix-dd-wide{min-width:560px;flex-direction:row;gap:12px;padding:10px 12px 12px}',
    '.scix-dd-col{display:flex;flex-direction:column;gap:2px;flex:1;min-width:0}',
    '.scix-dd-col+.scix-dd-col{border-left:1px solid rgba(255,255,255,.12);padding-left:12px}',
    '.scix-dd-head{font-size:.66rem;letter-spacing:.14em;color:#D2B65F;padding:6px 12px 4px;white-space:nowrap}',
    '.scix-nav-dd-menu a.scix-dd-all{font-weight:600;color:#fff}',

    '/* === Language switcher (inside the nav) === */',
    '/* 2026-09-17: made visible (中島「地味すぎてわからない」) — globe icon, bordered pill group, current language on white */',
    '.scix-lang{',
    '  display:flex;align-items:center;gap:2px;flex-shrink:0;',
    '  margin-left:14px;padding:3px 4px 3px 10px;',
    '  border:1px solid rgba(255,255,255,.38);border-radius:100px;',
    '}',
    '.scix-lang::before{',
    '  content:"";width:15px;height:15px;margin-right:5px;flex-shrink:0;opacity:.9;',
    '  background:url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'%23fff\' stroke-width=\'1.8\'%3E%3Ccircle cx=\'12\' cy=\'12\' r=\'9.5\'/%3E%3Cpath d=\'M2.5 12h19M12 2.5c3 3.2 3 15.8 0 19M12 2.5c-3 3.2-3 15.8 0 19\'/%3E%3C/svg%3E") center/contain no-repeat;',
    '}',
    '.scix-header-nav .scix-lang a{font-size:.74rem;font-weight:600;color:rgba(255,255,255,.88);padding:4px 9px;border-radius:100px;letter-spacing:.3px;line-height:1.3}',
    '.scix-header-nav .scix-lang a:hover{color:#fff;background:rgba(255,255,255,.16)}',
    '.scix-header-nav .scix-lang a.active{color:#1B2A4A;font-weight:700;background:#fff}',

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
    '  /* drawer: language row first, so it is seen the moment the menu opens */',
    '  .scix-lang{order:-1;margin:0 0 14px;padding:4px 6px 4px 12px;justify-content:flex-start;gap:4px;border:1px solid rgba(255,255,255,.38);border-radius:100px;align-self:flex-start;}',
    '  .scix-header-nav .scix-lang a{font-size:.88rem;padding:7px 14px;border-bottom:none;border-radius:100px;}',
    '  .scix-header-nav .scix-lang a.active{background:#fff;color:#1B2A4A}',
    '  .scix-nav-dd-menu.scix-dd-wide{min-width:0;flex-direction:column;gap:0;padding:2px 0}',
    '  .scix-dd-col+.scix-dd-col{border-left:none;padding-left:0;margin-top:2px}',
    '  .scix-dd-head{padding:10px 12px 2px 28px;font-size:.64rem}',
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
  //   ナレッジ (two columns: テーマで読む / はじめての方)
  // EN & 简中 = single inbound funnel for foreign capital → Home / Knowledge / Contact only.
  // items: [[href, label], ...] for a plain list, or
  //        [{head: 'テーマで読む', items: [[href, label, cls?], ...]}, ...] for a
  //        two-column menu. Anchor links (/knowledge#cat-…) carry no data-page so
  //        they never light up as "current".
  function ddLink(it) {
    var href = it[0], label = it[1], cls = it[2] || '';
    var page = href.indexOf('#') === -1 ? ' data-page="' + href + '"' : '';
    return '<a href="' + href + '"' + page + (cls ? ' class="' + cls + '"' : '') + '>' + label + '</a>';
  }
  function ddGroup(key, label, items) {
    var wide = !!(items.length && items[0] && items[0].items);
    var out = '<div class="scix-nav-dd" data-group="' + key + '">' +
      '<button type="button" class="scix-nav-dd-toggle" aria-expanded="false" aria-controls="scix-dd-' + key + '">' +
        label + '<span class="scix-dd-caret" aria-hidden="true">▾</span>' +
      '</button>' +
      '<div class="scix-nav-dd-menu' + (wide ? ' scix-dd-wide' : '') + '" id="scix-dd-' + key + '">';
    if (wide) {
      for (var c = 0; c < items.length; c++) {
        out += '<div class="scix-dd-col"><div class="scix-dd-head">' + items[c].head + '</div>';
        for (var j = 0; j < items[c].items.length; j++) out += ddLink(items[c].items[j]);
        out += '</div>';
      }
    } else {
      for (var i = 0; i < items.length; i++) out += ddLink(items[i]);
    }
    return out + '</div></div>';
  }

  // Pages that light up each group (beyond the links listed inside it).
  var GROUP_PAGES = {
    knowledge: ['/knowledge', '/qa', '/grid-storage'],
    buy:   ['/projects', '/transfer', '/fund', '/investors'],
    sell:  ['/sourcing', '/sourcing-criteria', '/land', '/partners', '/sell-form']
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
    // ナレッジ first: it is what visitors actually click (GA4 path: top → /knowledge
    // beats /company and /projects; column readers who continue go there too).
    ddGroup('knowledge', 'ナレッジ', [
      { head: 'テーマで読む', items: [
        ['/knowledge',            'すべての記事（毎週更新）', 'scix-dd-all'],
        ['/knowledge#cat-market', '収益・市場'],
        ['/knowledge#cat-rules',  '税制・制度・規制'],
        ['/knowledge#cat-deal',   '売買の実務'],
        ['/knowledge#cat-land',   '土地・用地'],
        ['/knowledge#cat-tech',   '技術・安全・運用']
      ]},
      { head: 'はじめての方', items: [
        ['/qa',              '入門Q&amp;A（24問）'],
        ['/column-somosomo', '蓄電池の、そもそも（連載20本）'],
        ['/grid-storage',    '蓄電池事業のしくみ']
      ]}
    ]),
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

  // --------------- 2b. 週1本の更新をメールで受け取る（JAのみ・2026-09-17 中島「つくって。入力はなるべく簡単に」） ---------------
  // 入力はメールアドレスだけ（お名前は任意）。受け口は scix-dealroom2 の /api/newsletter（D1に積む→毎朝
  // blastmail_sync.py がブラストメールへ登録）。置き場所: <div data-scix-newsletter> があればそこ、
  // 無ければ JA コラムの末尾（関連記事の下・フッターの上）。コラムの1記事1CTA（案件/フォーム）とは別物＝更新通知。
  var NL_API = 'https://scix-dealroom2.pages.dev/api/newsletter';
  var NL_SKIP = /^\/(contact|sell-form|thanks|privacy)$/;
  if (isJa && !NL_SKIP.test(loc)) {
    var nlCss = [
      '.scix-nl{max-width:760px;margin:40px auto 0;padding:26px 26px 22px;background:#1B2A4A;color:#fff;border-radius:10px;font-family:"Noto Sans JP",sans-serif;box-sizing:border-box}',
      '.scix-nl *{box-sizing:border-box}',
      '.scix-nl-label{font-size:.68rem;letter-spacing:.2em;color:#D2B65F;font-weight:700;margin-bottom:8px}',
      '.scix-nl h3{font-family:"Noto Serif JP",serif;font-size:1.08rem;font-weight:600;line-height:1.55;margin:0 0 6px;color:#fff}',
      '.scix-nl p{font-size:.84rem;line-height:1.8;color:rgba(255,255,255,.78);margin:0 0 16px}',
      '.scix-nl form{display:flex;flex-wrap:wrap;gap:8px}',
      '.scix-nl input{flex:1 1 200px;min-width:0;font:inherit;font-size:.95rem;padding:12px 14px;border:1px solid rgba(255,255,255,.28);border-radius:6px;background:#fff;color:#1B2A4A;outline:none}',
      '.scix-nl input:focus{border-color:#D2B65F;box-shadow:0 0 0 3px rgba(210,182,95,.25)}',
      '.scix-nl input.scix-nl-name{flex:0 1 160px}',
      '.scix-nl button{flex:0 0 auto;font:inherit;font-size:.92rem;font-weight:700;padding:12px 22px;background:#C49A3C;color:#1B2A4A;border:none;border-radius:6px;cursor:pointer;white-space:nowrap}',
      '.scix-nl button:hover{background:#D4AD5A}',
      '.scix-nl button[disabled]{opacity:.6;cursor:default}',
      '.scix-nl-note{font-size:.72rem;color:rgba(255,255,255,.55);line-height:1.7;margin:10px 0 0}',
      '.scix-nl-note a{color:rgba(255,255,255,.75)}',
      '.scix-nl-done{font-size:.95rem;font-weight:600;color:#E4C871;line-height:1.7}',
      '.scix-nl-err{font-size:.82rem;color:#FFB4A2;margin-top:8px}',
      '.scix-nl .scix-nl-hp{position:absolute;left:-9999px;width:1px;height:1px;opacity:0}',
      '@media(max-width:600px){.scix-nl{margin:32px 16px 0;padding:22px 18px 18px;border-radius:8px}.scix-nl input.scix-nl-name{flex:1 1 100%}.scix-nl button{flex:1 1 100%}}'
    ].join('\n');
    var nlStyle = document.createElement('style');
    nlStyle.id = 'scix-newsletter-css';
    nlStyle.textContent = nlCss;
    document.head.appendChild(nlStyle);

    var nlHtml = [
      '<div class="scix-nl-label">NEWSLETTER</div>',
      '<h3>週1本の新しい記事を、メールで受け取る</h3>',
      '<p>毎週1本、その週に書いた記事の要点とリンクをお送りします。メールアドレスだけで登録できます。</p>',
      '<form novalidate>',
      '  <input type="email" name="email" class="scix-nl-mail" placeholder="メールアドレス" autocomplete="email" inputmode="email" required aria-label="メールアドレス">',
      '  <input type="text" name="name" class="scix-nl-name" placeholder="お名前（任意）" autocomplete="name" aria-label="お名前（任意）">',
      '  <input type="text" name="_honey" class="scix-nl-hp" tabindex="-1" autocomplete="off" aria-hidden="true">',
      '  <button type="submit">受け取る</button>',
      '</form>',
      '<p class="scix-nl-note">配信は各メールの末尾からいつでも解除できます。アドレスは更新のお知らせにだけ使います（<a href="/privacy" target="_top">プライバシーポリシー</a>）。</p>'
    ].join('\n');

    function nlMount(el, where) {
      el.className = 'scix-nl';
      el.setAttribute('data-where', where);
      el.innerHTML = nlHtml;
      var form = el.querySelector('form');
      var mail = el.querySelector('.scix-nl-mail');
      var btn = el.querySelector('button');
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var email = (mail.value || '').trim();
        var name = (el.querySelector('.scix-nl-name').value || '').trim();
        var old = el.querySelector('.scix-nl-err');
        if (old) old.parentNode.removeChild(old);
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) {
          var er = document.createElement('div');
          er.className = 'scix-nl-err';
          er.textContent = 'メールアドレスの形をご確認ください。';
          form.parentNode.insertBefore(er, form.nextSibling);
          mail.focus();
          return;
        }
        btn.disabled = true;
        btn.textContent = '登録中…';
        var payload = { email: email, name: name, _honey: el.querySelector('.scix-nl-hp').value || '',
                        _page: path, _lang: 'ja' };
        fetch(NL_API, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                        body: JSON.stringify(payload) })
          .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
          .then(function (res) {
            if (!res.ok || !res.j || res.j.success !== true) throw new Error((res.j && res.j.error) || 'failed');
            var done = document.createElement('div');
            done.className = 'scix-nl-done';
            done.textContent = res.j.already
              ? 'このアドレスは登録済みです。次の記事からお届けします。'
              : '登録しました。次の記事からお届けします。';
            form.parentNode.replaceChild(done, form);
            try {
              if (typeof window.gtag === 'function') {
                window.gtag('event', 'newsletter_signup', { form_type: 'newsletter', placement: where,
                  page_lang: 'ja', already: res.j.already ? 1 : 0, transport_type: 'beacon' });
              }
            } catch (err) { /* ignore */ }
          })
          .catch(function () {
            btn.disabled = false;
            btn.textContent = '受け取る';
            var er2 = document.createElement('div');
            er2.className = 'scix-nl-err';
            er2.innerHTML = '送信できませんでした。お手数ですが <a href="mailto:s@scix.co.jp?subject=' +
              encodeURIComponent('ナレッジ更新メールの登録') + '&body=' + encodeURIComponent(email) +
              '" style="color:#fff">s@scix.co.jp</a> へ「更新メール希望」とお送りください。';
            form.parentNode.insertBefore(er2, form.nextSibling);
          });
      });
    }

    function nlPlace() {
      var slots = document.querySelectorAll('[data-scix-newsletter]');
      if (slots.length) {
        for (var s = 0; s < slots.length; s++) nlMount(slots[s], slots[s].getAttribute('data-scix-newsletter') || 'slot');
        return;
      }
      if (!isCol) return;
      var footer = document.querySelector('footer.scix-footer');
      if (!footer) return;
      var box = document.createElement('div');
      footer.parentNode.insertBefore(box, footer);
      // フッター直前は余白が詰まるので下に空ける
      box.style.marginBottom = '48px';
      nlMount(box, 'column');
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', nlPlace);
    else nlPlace();
  }

  // --------------- 3. Active page detection ---------------
  var links = header.querySelectorAll('.scix-header-nav a');
  // A column page lights up "すべての記事" only when no link names that page
  // exactly (e.g. /column-somosomo has its own row in the ナレッジ menu).
  var exactHit = false;
  for (var e0 = 0; e0 < links.length; e0++) {
    if (links[e0].getAttribute('data-page') === loc) { exactHit = true; break; }
  }
  for (var i = 0; i < links.length; i++) {
    var page = links[i].getAttribute('data-page');
    if (!page) continue;
    if (loc === page) {
      links[i].classList.add('active');
    }
    if (page === '/' && (loc === '' || loc === '/index')) {
      links[i].classList.add('active');
    }
    if (page === '/knowledge' && isCol && !exactHit) {
      links[i].classList.add('active');
    }
  }

  // --------------- 3b. Dropdown groups (ナレッジ / 買う / 売る) ---------------
  function isNarrowNow() {
    return !!(window.matchMedia && window.matchMedia('(max-width:' + BP + 'px)').matches);
  }
  function hoverCapable() {
    return !!(window.matchMedia && window.matchMedia('(hover:hover)').matches);
  }
  function trackOpen(group, by) {
    if (typeof window.gtag !== 'function') return;
    try {
      window.gtag('event', 'nav_open', {
        nav_group: group,
        open_by: by,
        page_lang: (document.documentElement.lang || 'ja'),
        transport_type: 'beacon'
      });
    } catch (err) { /* ignore */ }
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
      var holdsCurrent = pages.indexOf(loc) !== -1 || (key === 'knowledge' && isCol);
      if (holdsCurrent) {
        toggle.classList.add('active');
        dd.classList.add('is-current');
        // In the drawer, start with the visitor's own group unfolded.
        if (isNarrow) setOpen(dd, true);
      }
      // Click/tap toggle (touch + keyboard; desktop also opens on hover via CSS).
      toggle.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var willOpen = !dd.classList.contains('open');
        // Already visible through :hover → this click pins it, it is not a new open.
        var shownByHover = !isNarrowNow() && hoverCapable() && !!(dd.matches && dd.matches(':hover'));
        closeAllDropdowns(dd);
        setOpen(dd, willOpen);
        if (willOpen && !shownByHover) trackOpen(key, 'click');
      });
      // Keyboard: ArrowDown opens the group and moves focus to its first link;
      // Enter / Space keep the native button click. Focus leaving the group
      // (Tab past the last link) closes it so no menu is left hanging open.
      toggle.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowDown') return;
        e.preventDefault();
        var wasOpen = dd.classList.contains('open');
        closeAllDropdowns(dd);
        setOpen(dd, true);
        if (!wasOpen) trackOpen(key, 'keyboard');
        var first = dd.querySelector('.scix-nav-dd-menu a');
        if (first) first.focus();
      });
      var hoverCounted = false;
      dd.addEventListener('mouseenter', function () {
        if (isNarrowNow() || !hoverCapable()) return;
        // Only one menu at a time: a click-pinned neighbour folds when hovering here.
        closeAllDropdowns(dd);
        if (hoverCounted) return;
        hoverCounted = true;
        trackOpen(key, 'hover');
      });
      // WebKit does not focus buttons/links on pointer-down, so a tap inside the
      // group can fire focusout with relatedTarget=null before the click lands.
      var pointerInside = false;
      dd.addEventListener('pointerdown', function () {
        pointerInside = true;
        setTimeout(function () { pointerInside = false; }, 400);
      });
      dd.addEventListener('focusout', function (e) {
        if (isNarrowNow() || pointerInside) return;
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
    if (isOpen) trackOpen('drawer', 'click');
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
  // Crossing the breakpoint (iPad rotation, window resize): drop the state that
  // only makes sense in the other layout — an unfolded accordion would hang as a
  // floating dropdown on wide, an open drawer would leave the overlay + scroll
  // lock on wide with no burger to clear it.
  function onBreakpointChange() {
    if (isNarrowNow()) {
      closeAllDropdowns(null);
      for (var k = 0; k < dds.length; k++) {
        if (dds[k].classList.contains('is-current')) setOpen(dds[k], true);
      }
    } else {
      if (header.classList.contains('scix-header-open')) closeMenu();
      closeAllDropdowns(null);
    }
    syncInert();
  }
  var lastNarrow = isNarrowNow();
  function checkBreakpoint() {
    var n = isNarrowNow();
    if (n === lastNarrow) return;
    lastNarrow = n;
    onBreakpointChange();
  }
  if (window.matchMedia) {
    var mq = window.matchMedia('(max-width:' + BP + 'px)');
    if (mq.addEventListener) mq.addEventListener('change', checkBreakpoint);
    else if (mq.addListener) mq.addListener(checkBreakpoint);
  }
  // Belt and braces: some embedded/emulated viewports resize without a
  // MediaQueryList change event.
  window.addEventListener('resize', checkBreakpoint);

  burger.addEventListener('click', toggleMenu);
  overlay.addEventListener('click', closeMenu);

  // Same-document hash links (/knowledge#cat-…) do not navigate away, so a
  // click-pinned dropdown would otherwise stay open over the scrolled content.
  for (var j = 0; j < links.length; j++) {
    links[j].addEventListener('click', function () { closeMenu(); closeAllDropdowns(null); });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (isNarrowNow()) {
      // Drawer: close it, keep the accordion state (the current-page group stays unfolded).
      if (header.classList.contains('scix-header-open')) {
        closeMenu();
        burger.focus();
      }
      return;
    }
    var focused = document.activeElement;
    for (var k = 0; k < dds.length; k++) {
      if (dds[k].classList.contains('open') && focused && dds[k].contains(focused)) {
        var tg = dds[k].querySelector('.scix-nav-dd-toggle');
        if (tg) tg.focus();
      }
    }
    closeAllDropdowns(null);
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
  // knowledge / buy / sell（引き出しの中）・top（会社案内・お問い合わせ）・cta（金ボタン）・
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
