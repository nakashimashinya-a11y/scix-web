(function () {
  /* ======================================================
     ScienceX — Shared Navigation Header
     Single source of truth for all 26 pages.
     ====================================================== */

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
    '  display:flex;align-items:center;gap:6px;',
    '}',
    '.scix-header-nav a{',
    '  text-decoration:none;color:rgba(255,255,255,.7);',
    '  font-size:.82rem;font-weight:400;letter-spacing:.3px;',
    '  padding:8px 14px;border-radius:4px;',
    '  transition:color .25s,background .25s;',
    '  white-space:nowrap;',
    '}',
    '.scix-header-nav a:hover{color:#fff;background:rgba(255,255,255,.08)}',
    '.scix-header-nav a.active{color:#C49A3C;font-weight:500}',

    '/* === Contact CTA button (last link) === */',
    '.scix-header-nav a.scix-cta{',
    '  background:#C49A3C;color:#fff;font-weight:600;',
    '  padding:8px 20px;border-radius:4px;margin-left:8px;',
    '}',
    '.scix-header-nav a.scix-cta:hover{background:#D4AD5A}',
    '.scix-header-nav a.scix-cta.active{background:#D4AD5A;color:#fff}',

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

    '/* === Mobile breakpoint === */',
    '@media(max-width:768px){',
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
    '}'
  ].join('\n');

  var style = document.createElement('style');
  style.id = 'scix-header-css';
  style.textContent = css;
  document.head.appendChild(style);

  // --------------- 2. HTML ---------------
  var header = document.createElement('header');
  header.className = 'scix-header';
  header.id = 'scix-header';
  header.innerHTML = [
    '<div class="scix-header-overlay" id="scix-header-overlay"></div>',
    '<div class="scix-header-inner">',
    '  <a href="/" class="scix-header-logo"><img src="/img/logo-white.png" alt="ScienceX サイエンスエックス株式会社"></a>',
    '  <nav class="scix-header-nav" id="scix-header-nav">',
    '    <a href="/"          data-page="/">ホーム</a>',
    '    <a href="/bss"       data-page="/bss">蓄電池事業</a>',
    '    <a href="/knowledge" data-page="/knowledge">ナレッジ</a>',
    '    <a href="/company"   data-page="/company">会社案内</a>',
    '    <a href="/contact"   data-page="/contact" class="scix-cta">お問い合わせ</a>',
    '  </nav>',
    '  <button class="scix-header-burger" id="scix-header-burger" aria-label="メニューを開く" aria-expanded="false">',
    '    <span></span><span></span><span></span>',
    '  </button>',
    '</div>'
  ].join('\n');

  document.body.insertBefore(header, document.body.firstChild);

  // --------------- 3. Active page detection ---------------
  var path = window.location.pathname
    .replace(/\.html$/, '')
    .replace(/\/+$/, '') || '/';

  var links = header.querySelectorAll('.scix-header-nav a');
  for (var i = 0; i < links.length; i++) {
    var page = links[i].getAttribute('data-page');
    // Exact match
    if (path === page) {
      links[i].classList.add('active');
    }
    // Home aliases
    if (page === '/' && (path === '' || path === '/index')) {
      links[i].classList.add('active');
    }
    // Column articles → highlight ナレッジ
    if (page === '/knowledge' && path.indexOf('/column-') === 0) {
      links[i].classList.add('active');
    }
  }

  // --------------- 4. Hamburger toggle ---------------
  var burger = document.getElementById('scix-header-burger');
  var overlay = document.getElementById('scix-header-overlay');

  function toggleMenu() {
    var isOpen = header.classList.toggle('scix-header-open');
    document.body.style.overflow = isOpen ? 'hidden' : '';
    burger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    burger.setAttribute('aria-label', isOpen ? 'メニューを閉じる' : 'メニューを開く');
  }

  function closeMenu() {
    header.classList.remove('scix-header-open');
    document.body.style.overflow = '';
    burger.setAttribute('aria-expanded', 'false');
    burger.setAttribute('aria-label', 'メニューを開く');
  }

  burger.addEventListener('click', toggleMenu);
  overlay.addEventListener('click', closeMenu);

  // Close on nav link click (mobile)
  for (var j = 0; j < links.length; j++) {
    links[j].addEventListener('click', closeMenu);
  }

  // Close on Escape key
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && header.classList.contains('scix-header-open')) {
      closeMenu();
    }
  });
})();
