(function () {
  /* ======================================================
     ScienceX — Shared Navigation Header (JP + EN + 繁中)
     Single source of truth for all pages.
     ====================================================== */

  // --------------- 0. Language detection ---------------
  var path = window.location.pathname
    .replace(/\.html$/, '')
    .replace(/\/+$/, '') || '/';
  var isEn = path === '/en' || path.indexOf('/en/') === 0;
  var isZh = path === '/zh' || path.indexOf('/zh/') === 0 || path.indexOf('/zh-') === 0;
  var prefix = isEn ? '/en' : '';
  var logoHref = isZh ? '/zh' : (prefix + '/');

  // Canonical page id, shared across languages.
  // JP is the superset; EN/ZH are single-funnel subsets.
  var loc;
  if (isEn) {
    loc = path.replace(/^\/en/, '') || '/';
    if (loc === '/market-entry') loc = '/';
  } else if (isZh) {
    if (path === '/zh') loc = '/';
    else if (path === '/zh-knowledge') loc = '/knowledge';
    else if (path.indexOf('/zh-column-') === 0) loc = '/column-' + path.slice('/zh-column-'.length);
    else loc = path;
  } else {
    loc = path;
  }
  var isCol = loc.indexOf('/column-') === 0;

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
    '.scix-header-nav a{',
    '  text-decoration:none;color:rgba(255,255,255,.7);',
    '  font-size:.78rem;font-weight:400;letter-spacing:.1px;',
    '  padding:8px 9px;border-radius:4px;',
    '  transition:color .25s,background .25s;',
    '  white-space:nowrap;',
    '}',
    '.scix-header-nav a:hover{color:#fff;background:rgba(255,255,255,.08)}',
    '.scix-header-nav a.active{color:#C49A3C;font-weight:500}',

    '/* === Contact CTA button (last link) === */',
    '.scix-header-nav a.scix-cta{',
    '  background:#C49A3C;color:#fff;font-weight:600;',
    '  padding:8px 13px;border-radius:4px;margin-left:4px;',
    '}',
    '.scix-header-nav a.scix-cta:hover{background:#D4AD5A}',
    '.scix-header-nav a.scix-cta.active{background:#D4AD5A;color:#fff}',

    '/* === Language switcher === */',
    '.scix-lang{',
    '  display:flex;align-items:center;gap:3px;',
    '  margin-left:10px;background:rgba(255,255,255,.1);',
    '  border-radius:20px;padding:3px;flex-shrink:0;',
    '}',
    '.scix-lang a{',
    '  text-decoration:none;color:rgba(255,255,255,.6);',
    '  font-size:.85rem;font-weight:600;letter-spacing:.3px;',
    '  padding:5px 12px;border-radius:16px;transition:all .25s;',
    '  display:flex;align-items:center;gap:5px;',
    '}',
    '.scix-lang a:hover{color:#fff;background:rgba(255,255,255,.12)}',
    '.scix-lang a.active{color:#fff;background:#C49A3C;border-radius:16px}',

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
    '@media(max-width:1024px){',
    '  .scix-header-nav{',
    '    position:fixed;top:0;right:0;bottom:0;',
    '    width:280px;max-width:80vw;',
    '    background:#1B2A4A;',
    '    flex-direction:column;align-items:stretch;gap:0;',
    '    padding:80px 24px 40px;',
    '    transform:translateX(100%);',
    '    transition:transform .35s cubic-bezier(.4,0,.2,1);',
    '    z-index:10001;',
    '    box-shadow:-4px 0 24px rgba(0,0,0,.15);',
    '    overflow-y:auto;',
    '  }',
    '  .scix-header-open .scix-header-nav{transform:translateX(0)}',
    '  .scix-header-nav a{',
    '    padding:14px 16px;font-size:.92rem;',
    '    border-bottom:1px solid rgba(255,255,255,.06);',
    '    border-radius:0;',
    '  }',
    '  .scix-header-nav a.scix-cta{',
    '    margin:16px 0 0;text-align:center;',
    '    border-radius:4px;border-bottom:none;',
    '    padding:14px 20px;',
    '  }',
    '  .scix-header-burger{display:block}',
    '  .scix-lang{margin-left:auto;margin-right:12px}',
    '}'
  ].join('\n');

  var style = document.createElement('style');
  style.id = 'scix-header-css';
  style.textContent = css;
  document.head.appendChild(style);

  // --------------- 2. HTML (language-aware) ---------------
  // JP = full three-sided marketplace (investors / acquire / sell / land).
  // EN & 繁中 = single inbound funnel for foreign capital → Home / Knowledge / Contact only.
  var contactMail = 'mailto:s@scix.co.jp?subject=Japan%20BESS%20-%20Confidential%20briefing';
  var nav = isZh ? [
    '<a href="/zh"           data-page="/">首頁</a>',
    '<a href="/zh-knowledge" data-page="/knowledge">洞見</a>',
    '<a href="/zh-contact" class="scix-cta">聯絡我們</a>'
  ] : isEn ? [
    '<a href="/en"           data-page="/">Home</a>',
    '<a href="/en/knowledge" data-page="/knowledge">Knowledge</a>',
    '<a href="/en/contact" class="scix-cta">Contact</a>'
  ] : [
    '<a href="/"          data-page="/">ホーム</a>',
    '<a href="/investors" data-page="/investors">投資家の方へ</a>',
    '<a href="/transfer"  data-page="/transfer">案件を買う</a>',
    '<a href="/sourcing"  data-page="/sourcing">案件を売る</a>',
    '<a href="/land"      data-page="/land">用地</a>',
    '<a href="/company"   data-page="/company">会社案内</a>',
    '<a href="/knowledge" data-page="/knowledge">ナレッジ</a>',
    '<a href="/contact"   data-page="/contact" class="scix-cta">お問い合わせ</a>'
  ];

  // --------------- Language switcher (JA / EN / 繁中) ---------------
  // Targets resolve to the equivalent page where it exists, otherwise the
  // language home / knowledge hub — never a 404.
  var jpHref = isEn ? loc : (isZh ? (isCol ? '/knowledge' : loc) : path);

  var enHref;
  if (isEn) enHref = path;
  else if (loc === '/') enHref = '/en';
  else if (loc === '/knowledge') enHref = '/en/knowledge';
  else if (isCol) enHref = isZh ? '/en/knowledge' : ('/en' + loc);
  else enHref = '/en';

  var zhHref;
  if (isZh) zhHref = path;
  else if (loc === '/') zhHref = '/zh';
  else if (loc === '/knowledge' || isCol) zhHref = '/zh-knowledge';
  else zhHref = '/zh';

  var langSwitch = [
    '<div class="scix-lang">',
    '  <a href="' + jpHref + '"' + ((!isEn && !isZh) ? ' class="active"' : '') + '>🇯🇵 JP</a>',
    '  <a href="' + enHref + '"' + (isEn ? ' class="active"' : '') + '>🇺🇸 EN</a>',
    '  <a href="' + zhHref + '"' + (isZh ? ' class="active"' : '') + '>🇹🇼 繁中</a>',
    '</div>'
  ].join('\n');

  var burgerLabel = isEn ? 'Open menu' : (isZh ? '開啟選單' : 'メニューを開く');

  var header = document.createElement('header');
  header.className = 'scix-header';
  header.id = 'scix-header';
  header.innerHTML = [
    '<div class="scix-header-overlay" id="scix-header-overlay"></div>',
    '<div class="scix-header-inner">',
    '  <a href="' + logoHref + '" class="scix-header-logo"><img src="/img/logo-white.png" alt="ScienceX"></a>',
    '  <nav class="scix-header-nav" id="scix-header-nav">',
         nav.join('\n'),
    '  </nav>',
       langSwitch,
    '  <button class="scix-header-burger" id="scix-header-burger" aria-label="' + burgerLabel + '" aria-expanded="false">',
    '    <span></span><span></span><span></span>',
    '  </button>',
    '</div>'
  ].join('\n');

  document.body.insertBefore(header, document.body.firstChild);

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

  // --------------- 4. Hamburger toggle ---------------
  var burger = document.getElementById('scix-header-burger');
  var overlay = document.getElementById('scix-header-overlay');
  var openLabel = burgerLabel;
  var closeLabel = isEn ? 'Close menu' : (isZh ? '關閉選單' : 'メニューを閉じる');

  function toggleMenu() {
    var isOpen = header.classList.toggle('scix-header-open');
    document.body.style.overflow = isOpen ? 'hidden' : '';
    burger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    burger.setAttribute('aria-label', isOpen ? closeLabel : openLabel);
  }

  function closeMenu() {
    header.classList.remove('scix-header-open');
    document.body.style.overflow = '';
    burger.setAttribute('aria-expanded', 'false');
    burger.setAttribute('aria-label', openLabel);
  }

  burger.addEventListener('click', toggleMenu);
  overlay.addEventListener('click', closeMenu);

  for (var j = 0; j < links.length; j++) {
    links[j].addEventListener('click', closeMenu);
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && header.classList.contains('scix-header-open')) {
      closeMenu();
    }
  });
})();
