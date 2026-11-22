(function () {
  /* ======================================================
     ScienceX — Shared Navigation Header (JP + EN + 简中)
     Single source of truth for all pages.

     2026-11-22: 上の帯を蓄電所マーケットと同じ並びにした（買いたい・売りたい・ナレッジ・市場リサーチ・会社案内・お問い合わせ＋右端にログイン・無料で登録）。
       「買いたい」「売りたい」は札を押すとマーケットの画面へ直接行き（間の画面を挟まない）、横の ▾ だけが引き出しを開く（割りボタン）。
       「市場リサーチ」の引き出しに市場ノート・市場データを置いた（「買う」の引き出しにあった売り案件の市場データはここへ移した＝行き先は1か所に1回）。
       蓄電所マーケットの帯（dealroom の public/platform-nav.js）と同じ並び・同じ札の言葉。2つのリポジトリの並びは手で写す（docs/seo-change-log.md の行き先の表）。
       トップの案件カード（/site-cards.js）の出所の印は src=top-card（英語 -en・中国語 -zh）、placement=card。

     2026-11-06: 言語の切り替えが目立たなかったので、言語の切り替えをナビの外に出し、国旗
       （SVG）＋言語の名前（日本語 / English / 中文）・紺の太い枠・今の言語は
       紺地に白。スマホでは引き出しの中でなく、ヘッダーの帯に国旗を常に出す。
     2026-10-18: 案件を売る・買うを中心にする方針に合わせた。
       売る ▾ から「土地を売る・貸す」(/land) を外し、売却査定のフォーム
       (/sell-form) を入れた。/land と /sourcing-criteria は /sourcing へ 301。
       スマホの追従ボタンは、売主向けのページだけ /sell-form（売却査定）。
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
    else if (path === '/zh-glossary') loc = '/glossary';
    else if (path === '/zh-contact') loc = '/contact';
    else if (path === '/zh-thanks') loc = '/thanks';
    else if (path === '/zh-primer') loc = '/primer';
    else if (path === '/zh-company') loc = '/company';
    else if (path === '/zh-privacy') loc = '/privacy';
    else if (path.indexOf('/zh-column-') === 0) loc = '/column-' + path.slice('/zh-column-'.length);
    else if (path.indexOf('/zh-guide-') === 0) loc = '/guide-' + path.slice('/zh-guide-'.length);   // 柱の頁（scripts/build_guides.py）
    else loc = '/';
  } else {
    loc = path;
  }
  var isCol = loc.indexOf('/column-') === 0;

  // ページの側（色と絵）を <html data-side> に付ける。theme.css が帯の色・札の色・冒頭の絵を側ごとに替える
  // （2026-11-15: 蓄電所マーケットと同じ配色にそろえた。買う＝青・売る＝橙・読む＝紫）
  var side = loc === '/' ? 'home'
    : /^\/(transfer|projects|investors|market-data|fund|grid-storage|for\/)/.test(loc) ? 'buy'
    : /^\/(sourcing|sell-form|partners)/.test(loc) ? 'sell'
    : /^\/(knowledge|column-|guide-|report|glossary|qa|faq|primer|market-entry|citation)/.test(loc) ? 'read'
    : 'co';
  if (/^\/(projects|market-data)/.test(loc)) side = 'deal';
  document.documentElement.setAttribute('data-side', side);
  document.documentElement.setAttribute('data-page', loc);   // theme.css がページごとの冒頭の絵を選ぶ（お問い合わせ＝話す人・会社案内＝書類を確かめる人 など）

  // Columns that exist in Japanese only. Switching language from these must
  // fall back to the knowledge hub instead of a URL that does not exist.
  var JA_ONLY_COLUMNS = [
    '/column-investment-tax-law',
    '/column-investment-tax-practice',
    '/column-investment-tax-schedule',
    '/column-land-buyback',
    '/column-land-lease',
    '/column-land-zoning',
    '/column-study-reply',
    '/column-study-reply-2',
    '/column-study-reply-3',
    '/column-study-reply-4'
  ];
  // Columns with an English page but no Chinese page yet: the 简中 link goes to the Chinese knowledge hub.
  var NO_ZH_COLUMNS = [];
  // Pages with no Japanese counterpart. /grid-storage is the closest JA page
  // (it is the "what is grid-scale storage" explainer these two translate).
  var NO_JA_PAGE = { '/primer': '/grid-storage', '/market-entry-guide': '/grid-storage' };
  // Pages that exist in all three languages under language-specific slugs.
  var TRILINGUAL = {
    '/': { en: '/en', zh: '/zh' },
    '/projects': { en: '/en/projects', zh: '/zh' },
    '/knowledge': { en: '/en/knowledge', zh: '/zh-knowledge' },
    '/qa': { en: '/en/qa', zh: '/zh-qa' },
    '/faq': { en: '/en/faq', zh: '/zh' },
    '/glossary': { en: '/en/glossary', zh: '/zh-glossary' },
    '/contact': { en: '/en/contact', zh: '/zh-contact' },
    '/thanks': { en: '/en/thanks', zh: '/zh-thanks' },
    '/primer': { en: '/en/primer', zh: '/zh-primer' },
    '/market-entry-guide': { en: '/en/market-entry-guide', zh: '/zh' },
    '/press': { en: '/en/press', zh: '/zh' },
    '/company': { en: '/en/company', zh: '/zh-company' },
    '/privacy': { en: '/en/privacy', zh: '/zh-privacy' }
  };

  // Below this width the nav collapses into the drawer. The regrouped nav is
  // short enough that an iPad in landscape (1024px) keeps the full bar.
  var BP = 1100; // 2026-11-22: 札が8つ（買いたい・売りたい・ナレッジ・市場リサーチ・会社案内・お問い合わせ・ログイン・無料で登録）になったので 960 から上げた（2026-11-06: 900 だと 901〜955px でナビが右へはみ出していた）

  // --------------- 1. CSS ---------------
  var css = [
    '/* === ScienceX Header Reset === */',
    '.scix-header,.scix-header *,.scix-header *::before,.scix-header *::after{margin:0;padding:0;box-sizing:border-box}',

    '/* === Body offset for fixed header === */',
    'body{padding-top:64px!important}',

    '/* === Header bar === */',
    '/* 2026-11-15: 蓄電所マーケットと同じ、温かい白・丸み・側ごとの色にそろえた。ロゴは名刺と同じ紺のまま */',
    '.scix-header{',
    '  position:fixed;top:0;left:0;right:0;height:64px;',
    '  background:#fff;',
    '  z-index:9999;',
    '  border-bottom:2px solid #1F2A48;',
    '  font-family:"Noto Sans JP",sans-serif;',
    '}',

    '.scix-header-inner{',
    '  max-width:none;margin:0;height:100%;',
    '  display:flex;align-items:center;justify-content:space-between;',
    '  padding:0 24px;',
    '}',

    '/* === Logo === */',
    '.scix-header-logo{',
    '  text-decoration:none;display:flex;align-items:center;flex-shrink:0;',
    '}',
    '.scix-header-logo img{',
    '  height:38px;width:auto;display:block;',
    '}',

    '/* === Desktop nav === */',
    '.scix-header-nav{',
    '  display:flex;align-items:stretch;align-self:stretch;gap:2px;margin-left:22px;margin-right:auto;',
    '}',
    '.scix-header-nav > a,.scix-nav-dd-toggle,.scix-nav-main{',
    '  display:inline-flex;align-items:center;gap:8px;height:100%;',
    '  text-decoration:none;color:#1F2A48;',
    '  font-size:15px;font-weight:800;letter-spacing:0;line-height:1.3;',
    '  padding:0 14px;border-radius:0;',
    '  background:none;border:none;cursor:pointer;font-family:inherit;',
    '  transition:color .15s,background .15s,box-shadow .15s;',
    '  white-space:nowrap;--pc:#1F2A48;',
    '}',
    '.scix-ic{width:21px;height:21px;flex:0 0 auto;display:block;color:var(--pc)}',
    '.scix-nav-dd[data-group=knowledge] :is(.scix-nav-dd-toggle,.scix-nav-main){--pc:#7C4DDB}',
    '.scix-nav-dd[data-group=buy] :is(.scix-nav-dd-toggle,.scix-nav-main){--pc:#2563EB}',
    '.scix-nav-dd[data-group=sell] :is(.scix-nav-dd-toggle,.scix-nav-main){--pc:#D4610A}',
    '.scix-nav-dd[data-group=research] :is(.scix-nav-dd-toggle,.scix-nav-main){--pc:#138A62}',
    '.scix-header-nav > a.scix-top-buy{--pc:#2563EB}',
    '.scix-header-nav > a.scix-top-sell{--pc:#D4610A}',
    '.scix-header-nav > a[data-page="/report"]{--pc:#138A62}',
    '.scix-header-nav > a[data-page="/qa"]{--pc:#7C4DDB}',
    '.scix-header-nav > a[data-page="/knowledge"]{--pc:#7C4DDB}',
    '.scix-header-nav > a[data-page="/market-entry-guide"]{--pc:#2563EB}',
    '.scix-header-nav > a:hover,.scix-nav-dd-toggle:hover,.scix-nav-main:hover,.scix-nav-dd.split:hover :is(.scix-nav-main,.scix-dd-split-btn){color:#1F2A48;background:#F3F5FA;box-shadow:inset 0 -4px 0 var(--pc)}',
    '.scix-header-nav > a.active,.scix-nav-dd-toggle.active,.scix-nav-main.active{color:#fff;font-weight:900;background:var(--pc);box-shadow:none}',
    '.scix-header-nav > a.active .scix-ic,.scix-nav-dd-toggle.active .scix-ic,.scix-nav-main.active .scix-ic{color:#fff}',
    '/* 割りボタン（買いたい・売りたい）: 札は直接その画面へ、横の ▾ だけが引き出しを開く */',
    '.scix-nav-dd.split{gap:0}',
    '.scix-nav-main{padding-right:4px!important}',
    '.scix-dd-split-btn{padding:0 10px 0 4px!important;gap:0!important}',
    '/* 2026-11-22: ログイン・無料で登録は頁の案内の外（右端の1組）。ログインは枠だけの小さな丸、登録は橙の主ボタン */',
    '.scix-auth{display:flex;align-items:center;gap:10px;margin-left:16px;flex-shrink:0}',
    '.scix-auth-m{display:none}',
    '.scix-auth a.scix-login,.scix-auth-m a.scix-login{display:inline-flex;align-items:center;gap:6px;height:auto;padding:7px 14px 7px 11px;border:1.5px solid #C9D2E3;border-radius:999px;background:#fff;color:#1F2A48;font-size:14px;font-weight:700;line-height:1.3;text-decoration:none;white-space:nowrap;transition:border-color .15s,background .15s}',
    '.scix-auth a.scix-login svg,.scix-auth-m a.scix-login svg{width:18px;height:18px;flex:0 0 auto;display:block;color:#5B667A}',
    '.scix-auth a.scix-login:hover,.scix-auth-m a.scix-login:hover{border-color:#1F2A48;background:#F3F5FA}',
    '.scix-auth a.scix-mk,.scix-auth-m a.scix-mk{display:inline-flex;align-items:center;justify-content:center;height:auto;margin:0;padding:9px 18px;background:#D4610A;color:#fff;font-weight:900;font-size:15px;line-height:1.3;border-radius:999px;box-shadow:0 6px 16px rgba(212,97,10,.30);text-decoration:none;white-space:nowrap;transition:background .15s,box-shadow .15s,transform .15s}',
    '.scix-auth a.scix-mk:hover,.scix-auth-m a.scix-mk:hover{background:#EF7A1A;color:#fff;box-shadow:0 8px 20px rgba(212,97,10,.38);transform:translateY(-1px)}',
    '.scix-auth a:focus-visible,.scix-auth-m a:focus-visible{outline:2px solid #F97316;outline-offset:2px}',
    '.scix-en-tag{font-size:.66em;font-weight:800;color:#5B667A;border:1px solid #C9D2E3;border-radius:999px;padding:0 6px;margin-left:5px;line-height:1.6;white-space:nowrap}',
    '@media(max-width:1279px){.scix-ic{display:none}.scix-header-nav > a,.scix-nav-dd-toggle,.scix-nav-main{padding:0 9px;font-size:14px;gap:6px}.scix-nav-main{padding-right:3px}.scix-dd-split-btn{padding:0 8px 0 3px!important}.scix-header-nav{margin-left:10px}}',
    '@media(min-width:1280px) and (max-width:1360px){.scix-header-nav > a,.scix-nav-dd-toggle,.scix-nav-main{padding:0 10px;font-size:14px;gap:6px}.scix-ic{width:19px;height:19px}.scix-header-nav{margin-left:12px}.scix-nav-main{padding-right:4px}.scix-dd-split-btn{padding:0 8px 0 4px!important}}',
    '.scix-header-nav a:focus-visible,.scix-nav-dd-toggle:focus-visible,.scix-nav-main:focus-visible{outline:2px solid #F97316;outline-offset:2px}',

    '/* === Primary CTA button (black) === */',
    '.scix-header-nav a.scix-cta{',
    '  background:linear-gradient(135deg,#F97316,#F59E0B);color:#fff;font-weight:900;letter-spacing:0;',
    '  padding:10px 20px;border-radius:999px;margin-left:14px;box-shadow:0 6px 16px rgba(234,88,12,.30);',
    '}',
    '.scix-header-nav a.scix-cta:hover{filter:brightness(1.06);color:#fff;background:linear-gradient(135deg,#F97316,#F59E0B)}',
    '.scix-header-nav a.scix-cta.active{color:#fff;background:linear-gradient(135deg,#F97316,#F59E0B)}',

    '/* === Dropdown groups (ナレッジ / 買う / 売る) === */',
    '.scix-nav-dd{position:relative;display:flex;align-items:center;}',
    '.scix-nav-dd-toggle{display:inline-flex;align-items:center;gap:5px;}',
    '.scix-dd-caret{font-size:.7em;transition:transform .25s;opacity:.85}',
    '.scix-nav-dd-menu{',
    '  position:absolute;top:100%;left:0;min-width:224px;',
    '  background:#fff;border:0;border-radius:18px;',
    '  padding:8px;display:none;flex-direction:column;gap:2px;',
    '  box-shadow:0 18px 40px rgba(31,42,72,.18);z-index:10003;',
    '}',
    '.scix-nav-dd.open .scix-nav-dd-menu{display:flex}',
    '.scix-nav-dd.open .scix-dd-caret{transform:rotate(180deg)}',
    '/* hover-open only where a real pointer exists (not iPad / touch laptops in the wide layout) */',
    '@media(hover:hover){',
    '  .scix-nav-dd:hover .scix-nav-dd-menu{display:flex}',
    '  .scix-nav-dd:hover .scix-dd-caret{transform:rotate(180deg)}',
    '}',
    '.scix-nav-dd-menu a{padding:10px 12px;font-weight:500;border-radius:12px;color:#1F2A48;text-decoration:none;font-size:15px;line-height:1.5}',
    '.scix-nav-dd-menu a:hover{background:#FFF1E3;box-shadow:none}',
    '/* two-column menu (ナレッジ): テーマで読む | はじめての方 */',
    '.scix-nav-dd-menu.scix-dd-wide{min-width:560px;flex-direction:row;gap:12px;padding:10px 12px 12px}',
    '.scix-nav-dd-menu.scix-dd-wide.scix-dd-3{min-width:720px;max-width:calc(100vw - 240px)}',
    '.scix-dd-col{display:flex;flex-direction:column;gap:2px;flex:1;min-width:0}',
    '.scix-dd-col+.scix-dd-col{border-left:1px solid #E3E8F2;padding-left:12px}',
    '.scix-dd-head{font-family:"Inter Tight","Noto Sans JP",sans-serif;font-size:.72rem;font-weight:900;letter-spacing:.04em;color:#C2560A;padding:6px 12px 4px;white-space:nowrap}',
    '.scix-nav-dd-menu a.scix-dd-all{font-weight:900;color:#1F2A48}',

    '/* === Language switcher (next to the nav; flags + names) === */',
    '/* 2026-11-06: 言語の切り替えが目立たなかったため、国旗と色を付けて大きくした */',
    '/* 2026-09-17: made visible (it was too plain to notice) — globe icon, bordered pill group（→ 2026-11-06 に国旗へ） */',
    '.scix-lang{',
    '  display:flex;align-items:center;gap:3px;flex-shrink:0;',
    '  margin-left:14px;padding:3px;',
    '  border:2px solid #1F2A48;border-radius:100px;background:#fff;box-shadow:none;',
    '}',
    '.scix-lang a{',
    '  display:inline-flex;align-items:center;gap:7px;',
    '  font-family:"Inter Tight","Noto Sans JP","Noto Sans SC",sans-serif;',
    '  font-size:.88rem;font-weight:800;color:#1F2A48;text-decoration:none;',
    '  padding:5px 7px;border-radius:100px;line-height:1.3;white-space:nowrap;',
    '  transition:background .2s,color .2s;',
    '}',
    '.scix-lang a:hover{background:#E9EBF1;color:#1F2A48}',
    '.scix-lang-label{display:none}',
    '.scix-lang a.active{background:#1F2A48;color:#fff}',
    '.scix-flag{width:26px;height:17px;flex-shrink:0;display:block;border-radius:3px;box-shadow:0 0 0 1px rgba(0,0,0,.18)}',
    '.scix-lang a.active .scix-flag{box-shadow:0 0 0 2px #fff}',
    '/* 英語のナビは項目が多いので、1380px 以下では国旗だけ（2026-11-15 丸いボタンにして 1280px で右端が切れた） */',
    '@media(max-width:1380px){html[lang="en"] .scix-lang-label{display:none}html[lang="en"] .scix-lang a{padding:5px 7px;gap:0}html[lang="en"] .scix-header-nav a,html[lang="en"] .scix-nav-dd-toggle{padding:8px 9px}}',
    '/* 1100px 以下はナビと競るので、国旗だけにする（言語の名前は aria-label に残す） */',
    '@media(max-width:1120px){',
    '  .scix-lang-label{display:none}',
    '  .scix-lang a{padding:5px 7px;gap:0}',
    '}',

    '/* === Hamburger button (mobile only) === */',
    '.scix-header-burger{',
    '  display:none;background:none;border:none;cursor:pointer;',
    '  width:28px;height:20px;position:relative;z-index:10002;',
    '  flex-shrink:0;',
    '}',
    '.scix-header-burger span{',
    '  display:block;position:absolute;left:0;width:100%;height:2px;',
    '  background:#1F2A48;border-radius:2px;',
    '  transition:transform .3s,opacity .3s;',
    '}',
    '.scix-header-burger span:nth-child(1){top:0}',
    '.scix-header-burger span:nth-child(2){top:9px}',
    '.scix-header-burger span:nth-child(3){top:18px}',

    '/* Burger → X animation（閉じる印は金の X） */',
    '.scix-header-open .scix-header-burger span{background:#F97316;height:3px}',
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
    '    background:#FFFCF5;border-radius:22px 0 0 22px;',
    '    flex-direction:column;align-items:stretch;gap:0;',
    '    padding:76px 20px 32px;',
    '    transform:translateX(100%);',
    '    transition:transform .35s cubic-bezier(.4,0,.2,1);',
    '    z-index:10001;',
    '    box-shadow:-4px 0 24px rgba(0,0,0,.15);',
    '    overflow-y:auto;',
    '  }',
    '  .scix-header-open .scix-header-nav{transform:translateX(0)}',
    '  .scix-header-nav{margin:0}',
    '  .scix-ic{display:block}',
    '  .scix-header-nav > a,.scix-nav-dd-toggle,.scix-nav-main{',
    '    height:auto;padding:14px 12px;font-size:.95rem;gap:8px;',
    '    border-bottom:1px solid #EEE;',
    '    border-radius:12px;',
    '  }',
    '  .scix-auth{display:none}',
    '  .scix-auth-m{display:flex;flex-direction:column;gap:10px;padding:0 0 14px;margin-bottom:6px;border-bottom:1px solid #EEE}',
    '  .scix-auth-m a.scix-login{justify-content:center;padding:12px 20px;font-size:.95rem}',
    '  .scix-auth-m a.scix-mk{padding:13px 20px;font-size:.95rem}',
    '  /* 割りボタン: 札の行（直接その画面へ）と ▾（中身の行を開く）を1行に並べ、中身はその下に開く */',
    '  .scix-nav-dd.split{flex-direction:row;flex-wrap:wrap;align-items:stretch}',
    '  .scix-nav-dd.split .scix-nav-main{flex:1 1 0;min-width:0;padding:14px 12px!important}',
    '  .scix-nav-dd.split .scix-dd-split-btn{flex:0 0 56px;width:56px;justify-content:center;padding:14px 0!important}',
    '  .scix-nav-dd.split .scix-nav-dd-menu{flex:1 1 100%}',
    '  .scix-header-nav a:hover,.scix-nav-dd-toggle:hover,.scix-header-nav a.active,.scix-nav-dd-toggle.active{box-shadow:none}',
    '  .scix-header-nav a.scix-cta{',
    '    margin:18px 0 0;text-align:center;',
    '    border-radius:999px;border-bottom:none;',
    '    padding:14px 20px;',
    '  }',
    '  .scix-nav-dd{flex-direction:column;align-items:stretch;}',
    '  .scix-nav-dd-toggle{justify-content:flex-start;width:100%;text-align:left;}',
    '  .scix-nav-dd.split .scix-dd-split-btn .scix-dd-caret{margin-left:0}',
    '  .scix-nav-dd-toggle .scix-dd-caret{margin-left:auto}',
    '  .scix-nav-dd-toggle.active{background:none;}',
    '  .scix-nav-dd-menu{position:static;display:none;border:none;box-shadow:none;background:#FFF1E3;padding:2px 0;min-width:0;border-radius:14px;}',
    '  .scix-nav-dd:hover:not(.open) .scix-nav-dd-menu{display:none}',
    '  .scix-nav-dd:hover:not(.open) .scix-dd-caret{transform:none}',
    '  .scix-nav-dd.open .scix-nav-dd-menu{display:flex}',
    '  .scix-nav-dd.open .scix-dd-caret{transform:rotate(180deg)}',
    '  .scix-nav-dd-menu a{padding:12px 12px 12px 28px;font-size:.88rem;border-bottom:1px solid rgba(31,42,72,.06);border-radius:0;}',
    '  .scix-nav-dd-menu a:last-child{border-bottom:none}',
    '  /* header bar: flags always visible next to the burger (not hidden in the drawer) */',
    '  .scix-lang{margin:0 14px 0 auto;padding:2px;gap:2px}',
    '  .scix-lang a{padding:4px 6px;gap:0}',
    '  .scix-lang-label{display:none}',
    '  .scix-flag{width:27px;height:18px}',
    '  .scix-nav-dd-menu.scix-dd-wide{min-width:0;flex-direction:column;gap:0;padding:2px 0}',
    '  .scix-nav-dd-menu.scix-dd-wide.scix-dd-3{min-width:0;max-width:none}',
    '  .scix-dd-col+.scix-dd-col{border-left:none;padding-left:0;margin-top:2px}',
    '  .scix-dd-head{padding:10px 12px 2px 28px;font-size:.66rem}',
    '  .scix-header-burger{display:block}',
    '}'
  ].join('\n');

  // Floating mobile contact CTA — on mobile the nav collapses into the hamburger,
  // so keep a persistent, always-visible conversion path. white-on-black = WCAG AAA.
  css += "\n.scix-float-cta{position:fixed;right:16px;bottom:16px;z-index:9000;display:none;align-items:center;gap:7px;padding:13px 20px;background:linear-gradient(135deg,#F97316,#F59E0B);color:#fff;font-family:'Noto Sans JP',sans-serif;font-size:14px;font-weight:900;text-decoration:none;border-radius:999px;box-shadow:0 8px 22px rgba(234,88,12,.38)}.scix-float-cta:active{transform:translateY(1px)}.scix-float-cta svg{width:16px;height:16px}@media(max-width:768px){.scix-float-cta{display:inline-flex;opacity:0;transform:translateY(16px);pointer-events:none;transition:opacity .2s,transform .2s}.scix-float-cta.on{opacity:1;transform:none;pointer-events:auto}}";

  var style = document.createElement('style');
  style.id = 'scix-header-css';
  style.textContent = css;
  document.head.appendChild(style);

  // --------------- 2. HTML (language-aware) ---------------
  // JP = three-sided marketplace, grouped by what the visitor came to do:
  //   買う (buy a project / how buying works / hold via the fund)
  //   売る (sell a project or its rights / ask for a valuation / introduce)
  //   土地だけの買取・賃借はしない（2026-10-18）ので、土地の入口は置かない。
  //   ナレッジ (three columns: テーマで読む / はじめての方 / データ＝月報・市場データ・2026-11-02)
  // EN & 简中 = single inbound funnel for foreign capital → Home / Knowledge / Contact only.
  // items: [[href, label], ...] for a plain list, or
  //        [{head: 'テーマで読む', items: [[href, label, cls?], ...]}, ...] for a
  //        two-column menu. Anchor links (/knowledge#cat-…) carry no data-page so
  //        they never light up as "current".
  function ddLink(it) {
    var href = it[0], label = it[1], cls = it[2] || '';
    var page = href.indexOf('#') === -1 ? ' data-page="' + (it[3] || href) + '"' : '';   // it[3]＝言語をまたいだ頁の名前（英語の /en/report は '/report'）
    return '<a href="' + href + '"' + page + (cls ? ' class="' + cls + '"' : '') + '>' + label + '</a>';
  }
  function ddGroup(key, label, items, icon) {
    var wide = !!(items.length && items[0] && items[0].items);
    var out = '<div class="scix-nav-dd" data-group="' + key + '">' +
      '<button type="button" class="scix-nav-dd-toggle" aria-expanded="false" aria-controls="scix-dd-' + key + '">' +
        (icon ? ic(icon) : '') + '<span>' + label + '</span><span class="scix-dd-caret" aria-hidden="true">▾</span>' +
      '</button>' +
      '<div class="scix-nav-dd-menu' + (wide ? ' scix-dd-wide' : '') + (wide && items.length >= 3 ? ' scix-dd-3' : '') + '" id="scix-dd-' + key + '">';
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

  // 割りボタン（2026-11-22 買いたい・売りたい）: 札（a）は押すとその画面へ直接行き、横の ▾（button）だけが引き出しを開く。
  // 札の行き先はマーケットの入口＝間の画面を挟まない。引き出しの中身は当社の窓口（流れ・査定・ファンド・紹介）。
  function ddSplit(key, label, href, items, icon, caretLabel) {
    var out = '<div class="scix-nav-dd split" data-group="' + key + '">' +
      '<a class="scix-nav-main" href="' + href + '">' + (icon ? ic(icon) : '') + '<span>' + label + '</span></a>' +
      '<button type="button" class="scix-nav-dd-toggle scix-dd-split-btn" aria-expanded="false" aria-controls="scix-dd-' + key + '" aria-label="' + caretLabel + '">' +
        '<span class="scix-dd-caret" aria-hidden="true">▾</span></button>' +
      '<div class="scix-nav-dd-menu" id="scix-dd-' + key + '">';
    for (var i = 0; i < items.length; i++) out += ddLink(items[i]);
    return out + '</div></div>';
  }

  // 2026-11-15: マーケットの上の帯と同じ、色の付いた線の絵（買う＝青・売る＝橙・読む＝紫・市場ノート＝緑）
  var ICON = {
    book: '<path d="M3 5h6a3 3 0 0 1 3 3v12a2.5 2.5 0 0 0-2.5-2.5H3z"/><path d="M21 5h-6a3 3 0 0 0-3 3v12a2.5 2.5 0 0 1 2.5-2.5H21z"/>',
    buy: '<path d="M3 4h2.5l2.2 10.5h10.6L20.5 7H7"/><circle cx="9.5" cy="19" r="1.4"/><circle cx="17" cy="19" r="1.4"/>',
    sell: '<path d="M3 12.5V4h8.5L21 13.5 13.5 21z"/><circle cx="7.5" cy="8.5" r="1.4"/>',
    chart: '<path d="M3 20h18"/><path d="M6 16v-5M11 16V6M16 16v-8"/>',
    co: '<path d="M5 21V4h10v17M15 9h4v12M3 21h18"/><path d="M8 8h3M8 12h3M8 16h3"/>',
    mail: '<rect x="3" y="5" width="18" height="14"/><path d="M3 6l9 7 9-7"/>',
    home: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>',
    q: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .8-1 1.6V14"/><path d="M12 17.2v.1"/>',
    flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>'
  };
  function ic(k) { return '<svg class="scix-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" aria-hidden="true">' + ICON[k] + '</svg>'; }

  // Pages that light up each group (beyond the links listed inside it).
  var GROUP_PAGES = {
    knowledge: ['/knowledge', '/qa', '/grid-storage', '/glossary', '/column-somosomo', '/primer', '/market-entry-guide'],
    buy:   ['/projects', '/transfer', '/fund', '/investors', '/for/sme', '/for/major'],
    sell:  ['/sourcing', '/sell-form', '/partners', '/for/dealers'],
    research: ['/report', '/market-data']
  };

  // 2026-11-15 メニュー全体の見直し（重複をなくし、全体の整合をとった）:
  // 行き先は1か所に1回だけ。マーケット（案件を見る・リクエスト・自分で売る）は右端の橙のボタン1つにまとめ、
  // 買う・売るの中は当社の窓口（流れ・査定・ファンド・紹介）だけにする。市場ノートは上の段だけ（ナレッジの中に重ねない）。
  // 地域別の案件一覧（/projects・/en/projects）はマーケットの一覧と同じ中身なのでメニューから外す（ページは検索から来た人のために残す）。
  // 2026-11-22: 上の帯は蓄電所マーケット（platform-nav.js）と同じ並び: 買いたい・売りたい・ナレッジ・市場リサーチ・会社案内・お問い合わせ＋右端のログイン・無料で登録。
  // 「買いたい」「売りたい」はマーケットへ直接（日本語の売りたいは買主のリクエストの一覧 /needs・英語と中国語は /en/needs）。中国語の画面はマーケットに無いので英語の画面へ。
  // 札の言葉と行き先は、2つのリポジトリで同じ表を手で写す（片方の実行時にもう片方を読む形は、落ちたとき帯が欠けるので採らない）。
  var MKT = 'https://dealroom.scix.co.jp';
  var EN_TAG = '<span class="scix-en-tag">英文</span>';
  var nav = isZh ? [
    '<a href="' + MKT + '/en" class="scix-top-buy" data-k="buy">' + ic('buy') + '<span>购买</span></a>',
    '<a href="' + MKT + '/en/needs" class="scix-top-sell" data-k="sell">' + ic('sell') + '<span>出售</span></a>',
    ddGroup('knowledge', '洞见', [
      ['/zh-knowledge', '洞见', '', '/knowledge'],
      ['/zh-qa',        '问答', '', '/qa']
    ], 'book'),
    '<a href="/en/report" data-page="/report">' + ic('chart') + '<span>市场研究</span>' + EN_TAG + '</a>',
    '<a href="/zh-company" data-page="/company">' + ic('co') + '<span>公司介绍</span></a>',
    '<a href="/zh-contact" data-page="/contact">' + ic('mail') + '<span>联系我们</span></a>'
  ] : isEn ? [
    '<a href="' + MKT + '/en" class="scix-top-buy" data-k="buy">' + ic('buy') + '<span>Buy</span></a>',
    '<a href="' + MKT + '/en/needs" class="scix-top-sell" data-k="sell">' + ic('sell') + '<span>Sell</span></a>',
    ddGroup('knowledge', 'Knowledge', [
      ['/en/knowledge',          'Knowledge',   '', '/knowledge'],
      ['/en/qa',                 'Q&amp;A',     '', '/qa'],
      ['/en/market-entry-guide', 'Entry Guide', '', '/market-entry-guide']
    ], 'book'),
    ddGroup('research', 'Market Research', [
      ['/en/report',      'Market Notes', '', '/report'],
      ['/en/report/data', 'Market Data',  '', '/report/data']
    ], 'chart'),
    '<a href="/en/company" data-page="/company">' + ic('co') + '<span>Company</span></a>',
    '<a href="/en/contact" data-page="/contact">' + ic('mail') + '<span>Contact</span></a>'
  ] : [
    ddSplit('buy', '買いたい', MKT + '/', [
      ['/transfer', '買うまでの流れ・買い方3つ'],
      ['/fund',     'ファンドで持つ']
    ], 'buy', '買いたいのメニューを開く'),
    ddSplit('sell', '売りたい', MKT + '/needs', [
      ['/sell-form', '当社に無料で売却査定'],
      ['/sourcing',  '売るまでの流れ'],
      ['/partners',  '案件・投資家を紹介する']
    ], 'sell', '売りたいのメニューを開く'),
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
        ['/grid-storage',    '蓄電池事業のしくみ'],
        ['/glossary',        '用語集']
      ]}
    ], 'book'),
    // 市場リサーチ: 引き出しの中の札は、行き先の h1 と同じ言葉（O16-27）。売り案件の市場データは「買う」の引き出しからここへ移した（行き先は1か所に1回）
    ddGroup('research', '市場リサーチ', [
      ['/report',      '蓄電所の市場ノート'],
      ['/report/data', '蓄電所の市場データ'],
      ['/market-data', '系統用蓄電池の売り案件 市場データ']
    ], 'chart'),
    '<a href="/company"  data-page="/company">' + ic('co') + '<span>会社案内</span></a>',
    '<a href="/contact"  data-page="/contact">' + ic('mail') + '<span>お問い合わせ</span></a>'
  ];

  // 2026-11-22: ログイン・無料で登録は頁の案内ではなく利用者の操作なので、メニューの並びから外し、右端（言語の切り替えの手前）に隣り合わせで置く。
  // 広い画面は帯の右端の1組（.scix-auth）、畳んだメニューは開いた中の一番上の1組（.scix-auth-m）。同じ組を2か所に描いて、画面の幅でどちらかだけ見せる。
  var AUTH_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true" focusable="false"><circle cx="12" cy="8" r="3.6"/><path d="M5 20c.8-3.6 3.6-5.4 7-5.4s6.2 1.8 7 5.4"/></svg>';
  var AUTH = isZh ? { login: MKT + '/en/login', reg: MKT + '/en/register', lt: '登录', rt: '免费注册' }
           : isEn ? { login: MKT + '/en/login', reg: MKT + '/en/register', lt: 'Log in', rt: 'Sign up' }
           : { login: MKT + '/login', reg: MKT + '/register', lt: 'ログイン', rt: '無料で登録' };
  function authHtml(cls) {
    return '<div class="' + cls + '">' +
      '<a href="' + AUTH.login + '" class="scix-login">' + AUTH_ICON + '<span>' + AUTH.lt + '</span></a>' +
      '<a href="' + AUTH.reg + '" class="scix-mk scix-reg">' + AUTH.rt + '</a></div>';
  }

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
  else if (isCol) zhHref = (jaOnlyColumn || NO_ZH_COLUMNS.indexOf(loc) !== -1) ? '/zh-knowledge' : ('/zh-column-' + loc.slice('/column-'.length));
  else if (TRILINGUAL[loc]) zhHref = TRILINGUAL[loc].zh;
  else zhHref = '/zh';

  // Report pages (/report, /report/<month>, /en/report...): follow the page's own hreflang
  // alternates, so JP and EN land on the matching month and never on a month that has no English page.
  if (loc === '/report' || loc.indexOf('/report/') === 0) {
    var altPath = function (lang) {
      var l = document.querySelector('link[rel="alternate"][hreflang="' + lang + '"]');
      if (!l) return '';
      try { return new URL(l.href, window.location.href).pathname; } catch (e) { return ''; }
    };
    var altJa = altPath('ja'), altEn = altPath('en');
    if (isEn && altJa) jpHref = altJa;
    if (!isEn && altEn) enHref = altEn;
  }

  // 柱の頁（/guide-*・scripts/build_guides.py）: 言葉の対は頁の hreflang のとおり（無い言葉はその言葉のトップのまま）。
  if (loc.indexOf('/guide-') === 0) {
    var guideAlt = function (lang) {
      var l = document.querySelector('link[rel="alternate"][hreflang="' + lang + '"]');
      if (!l) return '';
      try { return new URL(l.href, window.location.href).pathname; } catch (e) { return ''; }
    };
    if (!isJa && guideAlt('ja')) jpHref = guideAlt('ja');
    if (!isEn && guideAlt('en')) enHref = guideAlt('en');
    if (!isZh && guideAlt('zh-CN')) zhHref = guideAlt('zh-CN');
  }

  // 国旗は SVG を直書き（絵文字の国旗は Windows で「JP」の文字に化けるので使わない）。
  var STAR = 'M0,-1 L0.2245,-0.309 0.9511,-0.309 0.3633,0.118 0.5878,0.809 0,0.382 -0.5878,0.809 -0.3633,0.118 -0.9511,-0.309 -0.2245,-0.309Z';
  var FLAG = {
    ja: '<svg class="scix-flag" viewBox="0 0 30 20" aria-hidden="true" focusable="false"><rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="6" fill="#BC002D"/></svg>',
    en: '<svg class="scix-flag" viewBox="0 0 60 30" aria-hidden="true" focusable="false"><clipPath id="scix-flag-uk"><path d="M30,15h30v15zv15H0zH0V0zV0h30z"/></clipPath><path d="M0,0v30h60V0z" fill="#012169"/><path d="M0,0L60,30M60,0L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0L60,30M60,0L0,30" clip-path="url(#scix-flag-uk)" stroke="#C8102E" stroke-width="4"/><path d="M30,0v30M0,15h60" stroke="#fff" stroke-width="10"/><path d="M30,0v30M0,15h60" stroke="#C8102E" stroke-width="6"/></svg>',
    zh: '<svg class="scix-flag" viewBox="0 0 30 20" aria-hidden="true" focusable="false"><rect width="30" height="20" fill="#DE2910"/><g fill="#FFDE00">' +
        '<path d="' + STAR + '" transform="translate(5,5) scale(3)"/>' +
        '<path d="' + STAR + '" transform="translate(10,2) rotate(239)"/>' +
        '<path d="' + STAR + '" transform="translate(12,4) rotate(262)"/>' +
        '<path d="' + STAR + '" transform="translate(12,7) rotate(-74)"/>' +
        '<path d="' + STAR + '" transform="translate(10,9) rotate(-51)"/>' +
        '</g></svg>'
  };
  function langLink(code, href, label, on) {
    return '<a href="' + href + '" hreflang="' + code + '" lang="' + code + '" aria-label="' + label + '"' +
      (on ? ' class="active" aria-current="true"' : '') + '>' +
      FLAG[code] + '<span class="scix-lang-label">' + label + '</span></a>';
  }
  var langSwitch = [
    '<div class="scix-lang" role="group" aria-label="' + (isEn ? 'Language' : (isZh ? '语言' : '言語')) + '">',
    '  ' + langLink('ja', jpHref, '日本語', isJa),
    '  ' + langLink('en', enHref, 'English', isEn),
    '  ' + langLink('zh', zhHref, '中文', isZh),
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
    '  <a href="' + logoHref + '" class="scix-header-logo"><img src="/img/logo-navy.png" alt="ScienceX" width="91" height="36" decoding="async"></a>',
    '  <nav class="scix-header-nav" id="scix-header-nav" aria-label="' + navLabel + '">',
         authHtml('scix-auth-m'),
         nav.join('\n'),
    '  </nav>',
       authHtml('scix-auth'),
       langSwitch,
    '  <button class="scix-header-burger" id="scix-header-burger" aria-label="' + burgerLabel + '" aria-expanded="false" aria-controls="scix-header-nav">',
    '    <span></span><span></span><span></span>',
    '  </button>',
    '</div>'
  ].join('\n');

  document.body.insertBefore(header, document.body.firstChild);

  // Floating contact CTA (mobile only; hidden on the contact/sell-form/thanks pages themselves)
  // 売主向けのページ（案件・権利を売る話）だけ、売却査定のフォームへ直行させる。
  if (!/contact|sell-form|thanks/.test(path)) {
    var isSellPage = ['/sourcing', '/partners', '/column-transfer', '/column-options', '/column-pricing'].indexOf(path) !== -1;
    var fcta = document.createElement('a');
    fcta.className = 'scix-float-cta';
    fcta.href = isSellPage ? '/sell-form' : (isZh ? '/zh-contact' : (isEn ? '/en/contact' : '/contact'));
    fcta.setAttribute('target', '_top');
    fcta.setAttribute('aria-label', isSellPage ? '無料で売却査定' : (isEn ? 'Contact us' : (isZh ? '咨询' : 'ご相談・お問い合わせ')));
    fcta.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>' + (isSellPage ? '無料で売却査定' : (isEn ? 'Contact' : (isZh ? '咨询' : '相談する')));
    document.body.appendChild(fcta);
    // 最初の画面では出さない（冒頭の主ボタンに重なって読めなかった＝2026-11-15 訪問者の目で歩いた点検）。1画面ぶん下へ進んだら出す
    var fctaTick = function () { fcta.classList.toggle('on', (window.scrollY || 0) > window.innerHeight * 0.9); };
    window.addEventListener('scroll', fctaTick, { passive: true }); fctaTick();
  }

  // --------------- 2b. 週1本の更新をメールで受け取る（JAのみ・2026-09-17 追加。入力はなるべく簡単に） ---------------
  // 入力はメールアドレスだけ（お名前は任意）。受け口は scix-dealroom2 の /api/newsletter（D1に積む→毎朝
  // blastmail_sync.py がブラストメールへ登録）。置き場所: <div data-scix-newsletter> があればそこ、
  // 無ければ JA コラムの末尾（関連記事の下・フッターの上）。コラムの1記事1CTA（案件/フォーム）とは別物＝更新通知。
  var NL_API = 'https://dealroom.scix.co.jp/api/newsletter';
  var NL_SKIP = /^\/(contact|sell-form|thanks|privacy)$/;
  if (isJa && !NL_SKIP.test(loc)) {
    var nlCss = [
      '.scix-nl{max-width:760px;margin:40px auto 0;padding:26px 26px 22px;background:linear-gradient(118deg,#D4C6FF 0%,#EFE8FF 52%,#FFDDF0 100%);color:#0B1530;border-radius:24px;box-shadow:0 14px 32px rgba(31,42,72,.12);font-family:"Noto Sans JP",sans-serif;box-sizing:border-box}',
      '.scix-nl *{box-sizing:border-box}',
      '.scix-nl-label{display:inline-flex;font-family:"Inter Tight","Noto Sans JP",sans-serif;font-size:.76rem;letter-spacing:.02em;color:#5B32B5;background:#fff;border-radius:999px;padding:4px 12px;font-weight:900;margin-bottom:10px;box-shadow:0 2px 8px rgba(31,42,72,.08)}',
      '.scix-nl h3{font-family:"Noto Sans JP",sans-serif;font-size:1.15rem;font-weight:900;line-height:1.55;margin:0 0 6px;color:#0B1530}',
      '.scix-nl p{font-size:.86rem;line-height:1.8;color:#24304A;margin:0 0 16px}',
      '.scix-nl form{display:flex;flex-wrap:wrap;gap:8px}',
      '.scix-nl input{flex:1 1 200px;min-width:0;font:inherit;font-size:.95rem;padding:12px 14px;border:2px solid #fff;border-radius:999px;background:#fff;color:#1F2A48;outline:none}',
      '.scix-nl input:focus{border-color:#7C4DDB;box-shadow:0 0 0 3px rgba(124,77,219,.25)}',
      '.scix-nl input.scix-nl-name{flex:0 1 160px}',
      '.scix-nl button{flex:0 0 auto;font:inherit;font-size:.92rem;font-weight:700;padding:12px 24px;background:linear-gradient(135deg,#F97316,#F59E0B);color:#fff;font-weight:900;border:none;border-radius:999px;cursor:pointer;white-space:nowrap;box-shadow:0 6px 16px rgba(234,88,12,.30)}',
      '.scix-nl button:hover{filter:brightness(1.06)}',
      '.scix-nl button[disabled]{opacity:.6;cursor:default}',
      '.scix-nl-note{font-size:.74rem;color:#4A5568;line-height:1.7;margin:10px 0 0}',
      '.scix-nl-note a{color:#5B32B5}',
      '.scix-nl-done{font-size:.95rem;font-weight:800;color:#0F7A52;line-height:1.7}',
      '.scix-nl-err{font-size:.82rem;color:#B42318;margin-top:8px}',
      '.scix-nl .scix-nl-hp{position:absolute;left:-9999px;width:1px;height:1px;opacity:0}',
      '.scix-nl.scix-nl-rp{background:linear-gradient(118deg,#BDEBD6 0%,#E8F8F0 52%,#FFF0D6 100%)}',
      '.scix-nl.scix-nl-rp .scix-nl-label{color:#0F7A52}',
      '.scix-nl.scix-nl-rp input:focus{border-color:#138A62;box-shadow:0 0 0 3px rgba(19,138,98,.22)}',
      '@media(max-width:600px){.scix-nl{margin:32px 16px 0;padding:22px 18px 18px;border-radius:20px}.scix-nl input.scix-nl-name{flex:1 1 100%}.scix-nl button{flex:1 1 100%}}'
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
      '  <input type="text" name="_honey" class="scix-nl-hp" tabindex="-1" autocomplete="off">',
      '  <button type="submit">受け取る</button>',
      '</form>',
      '<p class="scix-nl-note">配信は各メールの末尾からいつでも解除できます。アドレスは更新のお知らせにだけ使います（<a href="/privacy" target="_top">プライバシーポリシー</a>）。</p>'
    ].join('\n');

    // 2026-11-21: 市場ノート（/report・/report/<月>）にも登録の箱を出す。
    // 受け口は記事の箱と同じ /api/newsletter（_page に /report… が残るので、どの箱から来たかは名簿の page で分かる）。置き場所の名前は report_index／report_issue。
    // 文は今の約束（週1本の記事）のまま。毎月の号をメールで送る形にするときは、文もそれに合わせて替える。
    var isReportPage = loc === '/report' || /^\/report\/\d{4}-\d{2}$/.test(loc);

    function nlMount(el, where, isRp) {
      el.className = 'scix-nl' + (isRp ? ' scix-nl-rp' : '');
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
          er.setAttribute('role', 'alert');
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
            done.setAttribute('role', 'status');
            done.setAttribute('tabindex', '-1');
            done.textContent = res.j.unsubscribed
              ? 'このアドレスは以前に配信を停止されています。再開をご希望の場合は s@scix.co.jp へ「更新メール再開希望」とお送りください。'
              : (res.j.already
                ? 'このアドレスは登録済みです。次の記事からお届けします。'
                : '登録しました。次の記事からお届けします。');
            form.parentNode.replaceChild(done, form);
            try { done.focus(); } catch (err) { /* ignore */ }
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
            er2.setAttribute('role', 'alert');
            er2.innerHTML = '送信できませんでした。お手数ですが <a href="mailto:s@scix.co.jp?subject=' +
              encodeURIComponent('ナレッジ更新メールの登録') + '&body=' + encodeURIComponent(email) +
              '" style="color:#5B32B5">s@scix.co.jp</a> へ「更新メール希望」とお送りください。';
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
      if (isReportPage) {
        try {
          // 号の頁は「蓄電所マーケットで案件を見る」の帯（section.cta）の上、一覧の頁はフッターの上
          var at = document.querySelector('section.cta') || document.querySelector('footer.scix-footer');
          if (!at) return;
          var rbox = document.createElement('div');
          at.parentNode.insertBefore(rbox, at);
          rbox.style.marginBottom = '48px';
          nlMount(rbox, loc === '/report' ? 'report_index' : 'report_issue', true);
        } catch (err) { /* 箱を出せなくても頁はそのまま */ }
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
    if (page === '/report' && loc.indexOf('/report') === 0) {
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
      var main = dd.querySelector('.scix-nav-main');   // 割りボタンの札（買いたい・売りたい）
      var holdsCurrent = pages.indexOf(loc) !== -1 || (key === 'knowledge' && isCol) ||
        (key === 'research' && (loc === '/report' || loc.indexOf('/report/') === 0));   // 市場ノートの号は「市場リサーチ」が光る（2026-11-22）
      if (holdsCurrent) {
        toggle.classList.add('active');
        if (main) main.classList.add('active');
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
    var a = t && t.closest ? t.closest('.scix-header-nav a, .scix-auth a, .scix-lang a, .scix-header-logo') : null;
    if (!a || typeof window.gtag !== 'function') return;
    var group;
    if (a.classList.contains('scix-header-logo')) group = 'logo';
    else if (a.classList.contains('scix-cta') || a.classList.contains('scix-mk') || a.classList.contains('scix-login')) group = 'cta';   // 蓄電所マーケットのボタン（無料で登録・ログイン）も cta に数える（2026-11-15）
    else if (a.classList.contains('scix-top-buy') || a.classList.contains('scix-top-sell')) group = a.getAttribute('data-k') || 'top';   // 英語・中国語の買う・売る（引き出しなし）
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

  // --------------- 7. 測る仕組み（2026-11-21） ---------------
  // 読まれた後が数えられていなかった（サイトから蓄電所マーケットへのリンクに出所の印が0・問い合わせにどの頁から来たかが残らない）。
  // 全頁が読むこのファイルで足す。どれも try の中＝失敗しても今の表示とナビは変わらない。
  //  7a. 出所の印: dealroom.scix.co.jp へのリンクを押す（触る）直前に ?src=<頁の印> を足す（すでに src があれば替えない・lang などは残す）。
  //      印の形はマーケット側の public/src-mark.js・functions/_lib/signup_src.ts と同じ＝英数と _- だけ・64字まで。
  //      コラム col-<slug>／市場ノート report・report-<YYYY-MM>／ナレッジの一覧 knowledge／トップ top／ほかは site-<頁>。英語は末尾に -en、中国語は -zh。
  //      頁を読み込んだ時点では href を変えない（検索エンジンが読むリンクは今のまま）。
  //  7b. GA4: マーケットへのリンクが押されたら market_click を1回（from_path・src_mark・placement＝header/card/hero/body/end/footer・link_path）。
  //      前からの dr2_promo_click・dr2_register_click（各頁の onclick）は内訳として残し、legacy_event・legacy_target に写す＝マーケットへの送客は market_click だけで数える（足さない）。
  //  7c. 社内の閲覧の印: 一度 ?internal=1 を開いた端末は、GA4 の利用者の印 internal_user=1 を付ける（?internal=0 で外す・localStorage）。
  //      GA4 のデータフィルタが読む traffic_type=internal は、各頁の head の GA の区画（scripts/build_ga_tag.py・同じ鍵 scix_internal）が config に付ける
  //      （config は head で先に走るので、ここでは付けられない）。同じ区画が、本番以外の住所と自動操作のブラウザからは送らない。
  //  7d. 問い合わせの出所: 最初に着いた頁・その前のサイト（ホスト名だけ）・直前に見ていた頁・出所の印（src・utm）を sessionStorage に覚え、
  //      /api/contact へ送るフォームに隠し欄（_entry_page・_entry_ref・_prev_page・_src・_utm）で渡す。受け口（web-contact.ts）は「_」で始まる欄を
  //      断らずに本文から外すので、今は届いても残らない（受け口に記録の行を足せば残る）。頁の住所は path だけ（問い合わせの引数は持たない）。
  //  7e. 記事 → 市場ノート: 需給調整市場・卸電気・容量市場の記事に、/report/latest.json（build_reports.py が焼く）の「最新の数字」の札を出す。
  //      JSON が読めなければ出さない。札の文は号の頁の「今月の動き」の文そのまま（言い直さない）。
  //  7f. 導線の押下: a[data-cta] が押されたら cta_click（placement・target・src_mark）を1回（2026-11-22）。
  try { (function () {
    var MARKET_HOST = 'dealroom.scix.co.jp';
    var langSfx = isEn ? '-en' : (isZh ? '-zh' : '');
    var lang = isEn ? 'en' : (isZh ? 'zh' : 'ja');
    function cleanMark(v) {
      return String(v == null ? '' : v).replace(/[^A-Za-z0-9_-]+/g, '-').replace(/-{2,}/g, '-').replace(/^-+|-+$/g, '');
    }
    function pageMark() {
      var m;
      if (isCol) m = 'col-' + loc.slice('/column-'.length);
      else if (loc === '/report') m = 'report';
      else if (/^\/report\/\d{4}-\d{2}$/.test(loc)) m = 'report-' + loc.slice('/report/'.length);
      else if (loc === '/knowledge') m = 'knowledge';
      else if (loc === '/' || loc === '/index') m = (isZh && path !== '/zh') ? 'site-' + path.replace(/^\/zh-?/, '') : 'top';
      else m = 'site-' + loc.replace(/^\/+/, '');
      m = cleanMark(m) || 'site';
      return m.slice(0, 64 - langSfx.length).replace(/-+$/, '') + langSfx;
    }
    var MARK = pageMark();
    window.SCIX_SRC_MARK = MARK;   // 確かめ用（ほかからは使わない）
    // トップの案件カード（data-placement="card"）の出所の印は top-card（英語 -en・中国語 -zh）。GA4 の placement も card
    var CARD_MARK = ('top-card' + langSfx);
    function markOf(a) { return a && a.closest && a.closest('[data-placement="card"]') ? CARD_MARK : MARK; }

    // ---- 7a. 出所の印 ----
    function marketUrl(a) {
      try {
        var href = a && a.getAttribute && a.getAttribute('href');
        if (!href) return null;
        var u = new URL(href, window.location.href);
        return u.hostname === MARKET_HOST ? u : null;
      } catch (err) { return null; }
    }
    function tagLink(a) {
      var u = marketUrl(a);
      if (!u) return null;
      try {
        if (!/(?:^|[?&])src=/.test(u.search)) {
          u.search = (u.search && u.search.length > 1 ? u.search + '&' : '?') + 'src=' + markOf(a);
          a.setAttribute('href', u.toString());
        }
      } catch (err) { /* 印を足せなくてもリンクはそのまま */ }
      return u;
    }
    function linkOf(e) {
      var t = e && e.target;
      if (t && t.nodeType !== 1) t = t.parentNode;
      return t && t.closest ? t.closest('a[href]') : null;
    }
    var touch = function (e) { try { var a = linkOf(e); if (a) tagLink(a); } catch (err) { /* ignore */ } };
    document.addEventListener('mousedown', touch, true);
    document.addEventListener('touchstart', touch, { capture: true, passive: true });
    document.addEventListener('focusin', touch, true);

    // ---- 7b. GA4 market_click（1回の押下に1回） ----
    function placementOf(a) {
      if (a.closest('[data-placement="card"]')) return 'card';
      if (a.closest('.scix-header')) return 'header';
      if (a.closest('footer, .scix-footer')) return 'footer';
      var ab = document.querySelector('.author-box');
      if (ab && (ab.contains(a) || (ab.compareDocumentPosition(a) & 4))) return 'end';   // 4 = 著者欄より後ろ（本文の末尾の導線）
      if (a.closest('section.cta, .cta, [data-scix-related]')) return 'end';
      if (a.closest('.hero, [class*="hero"]')) return 'hero';
      return 'body';
    }
    function onClick(e) {
      try {
        if (e.type === 'auxclick' && e.button !== 1) return;
        var a = linkOf(e);
        if (!a) return;
        var u = tagLink(a);
        if (!u || typeof window.gtag !== 'function') return;
        var lm = /(dr2_[a-z]+_click)'\s*,\s*\{\s*target\s*:\s*'([^']*)'/.exec(a.getAttribute('onclick') || '');
        window.gtag('event', 'market_click', {
          page_path: path, from_path: path, src_mark: markOf(a), placement: placementOf(a), link_path: u.pathname,
          legacy_event: lm ? lm[1] : '', legacy_target: lm ? lm[2] : '',
          page_lang: (document.documentElement.lang || lang), transport_type: 'beacon'
        });
      } catch (err) { /* ignore */ }
    }
    document.addEventListener('click', onClick, true);
    document.addEventListener('auxclick', onClick, true);

    // ---- 7f. 導線の押下 cta_click（2026-11-22・a[data-cta] の委任） ----
    // 記事の途中・末尾などの導線は <a data-cta="<置き場>" data-cta-target="<行き先の名>" href="…"> と書く（onclick は書かない）。
    // placement＝data-cta の値（例 mid・end）、target＝data-cta-target（無ければ行き先から market／contact／sell_form／site-<頁>）、
    // src_mark＝頁の印（7a と同じ）、from_path＝押した頁の道（page_path は gtag が予約語として外して届かないので使わない）。前からの onclick で cta_click を送っているリンクには足さない（二重に数えない）。
    // マーケットへのリンクは、7b の market_click も今のまま1回出る（送客の数は market_click で数える）。
    function ctaTarget(a) {
      var t = cleanMark(a.getAttribute('data-cta-target'));
      if (t) return t.slice(0, 64);
      var u = null;
      try { u = new URL(a.getAttribute('href') || '', window.location.href); } catch (err) { return 'other'; }
      if (u.hostname === MARKET_HOST) return 'market';
      if (u.hostname !== window.location.hostname) return 'external';
      var p = u.pathname.replace(/\.html$/, '');
      if (/^\/(?:en\/|zh-)?contact$/.test(p)) return 'contact';
      if (/^\/(?:en\/)?sell-form$/.test(p)) return 'sell_form';
      return (cleanMark('site-' + p.replace(/^\/+/, '')) || 'site').slice(0, 64);
    }
    function onCta(e) {
      try {
        if (e.type === 'auxclick' && e.button !== 1) return;
        var a = linkOf(e);
        if (!a || !a.hasAttribute('data-cta') || typeof window.gtag !== 'function') return;
        if (/'cta_click'/.test(a.getAttribute('onclick') || '')) return;
        var lp = '';
        try { lp = new URL(a.getAttribute('href') || '', window.location.href).pathname; } catch (err) { lp = ''; }
        window.gtag('event', 'cta_click', {
          placement: (cleanMark(a.getAttribute('data-cta')) || 'body').slice(0, 40), target: ctaTarget(a),
          src_mark: markOf(a), from_path: path, link_path: lp,
          page_lang: (document.documentElement.lang || lang), transport_type: 'beacon'
        });
      } catch (err) { /* ignore */ }
    }
    document.addEventListener('click', onCta, true);
    document.addEventListener('auxclick', onCta, true);

    // ---- 7c. 社内の閲覧の印 ----
    var INT_KEY = 'scix_internal';
    var qs = null;
    try { qs = new URLSearchParams(window.location.search); } catch (err) { qs = null; }
    var qi = qs ? qs.get('internal') : null;
    var internal = false;
    try {
      if (qi === '1') window.localStorage.setItem(INT_KEY, '1');
      else if (qi === '0') window.localStorage.removeItem(INT_KEY);
      internal = window.localStorage.getItem(INT_KEY) === '1';
    } catch (err) { internal = qi === '1'; }
    if (internal) {
      try {
        var props = { internal_user: '1' };
        var dl = window.dataLayer, done = false;
        // gtag.js がまだ読み込まれていなければ（dataLayer がただの配列）、最初の page_view より前に印を差し込む
        if (dl && dl.push === Array.prototype.push) {
          for (var di = 0; di < dl.length; di++) {
            if (dl[di] && dl[di][0] === 'config') {
              dl.splice(di, 0, (function () { return arguments; })('set', 'user_properties', props));
              done = true;
              break;
            }
          }
        }
        if (!done && typeof window.gtag === 'function') window.gtag('set', 'user_properties', props);
      } catch (err) { /* ignore */ }
    }
    if (qi === '1' || qi === '0') {
      var showToast = function () {
        try {
          var tst = document.createElement('div');
          tst.setAttribute('role', 'status');
          tst.style.cssText = 'position:fixed;left:16px;bottom:16px;z-index:10050;max-width:calc(100vw - 32px);background:#1F2A48;color:#fff;font:700 13px/1.6 "Noto Sans JP",sans-serif;padding:10px 16px;border-radius:14px;box-shadow:0 8px 22px rgba(31,42,72,.3)';
          tst.textContent = qi === '1' ? 'この端末の閲覧に社内の印を付けました（外すときは ?internal=0）' : 'この端末の社内の印を外しました';
          document.body.appendChild(tst);
          setTimeout(function () { if (tst.parentNode) tst.parentNode.removeChild(tst); }, 5000);
        } catch (err) { /* ignore */ }
      };
      if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', showToast); else showToast();
    }

    // ---- 7d. 問い合わせの出所 ----
    var entry = null, prev = '', mark = {};
    try {
      var SS = window.sessionStorage;
      try { entry = JSON.parse(SS.getItem('scix_entry') || 'null'); } catch (err) { entry = null; }
      if (!entry || typeof entry !== 'object') {
        var ref = '';
        try {
          if (document.referrer) {
            var ru = new URL(document.referrer);
            if (ru.hostname && ru.hostname !== window.location.hostname) ref = ru.hostname.slice(0, 100);
          }
        } catch (err) { ref = ''; }
        entry = { p: path.slice(0, 200), r: ref };
        SS.setItem('scix_entry', JSON.stringify(entry));
      }
      var cur = SS.getItem('scix_cur');
      if (cur && cur !== path) SS.setItem('scix_prev', cur);
      SS.setItem('scix_cur', path);
      prev = SS.getItem('scix_prev') || '';
      if (prev === path) prev = '';
      try { mark = JSON.parse(SS.getItem('scix_mark') || '{}') || {}; } catch (err) { mark = {}; }
      if (qs && !mark.src && !mark.utm_source) {
        var MK_KEYS = ['src', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];
        var gotMk = {}, anyMk = false;
        for (var mk = 0; mk < MK_KEYS.length; mk++) {
          var mv = String(qs.get(MK_KEYS[mk]) || '').trim().slice(0, 64);
          if (mv && /^[A-Za-z0-9_.-]+$/.test(mv)) { gotMk[MK_KEYS[mk]] = mv; anyMk = true; }
        }
        if (anyMk) { mark = gotMk; SS.setItem('scix_mark', JSON.stringify(mark)); }
      }
    } catch (err) { /* sessionStorage が使えない環境＝隠し欄は付けない */ }
    function utmText() {
      var out = [];
      for (var k in mark) {
        if (Object.prototype.hasOwnProperty.call(mark, k) && k.indexOf('utm_') === 0) out.push(k + '=' + mark[k]);
      }
      return out.join(';');
    }
    function putHidden(f, name, val) {
      if (!val || f.querySelector('input[name="' + name + '"]')) return;
      var i = document.createElement('input');
      i.type = 'hidden'; i.name = name; i.value = String(val).slice(0, 200);
      f.appendChild(i);
    }
    function fillForms() {
      try {
        if (!entry) return;
        var forms = document.querySelectorAll('form');
        for (var fi = 0; fi < forms.length; fi++) {
          var f = forms[fi];
          if (!/\/api\/contact$/.test(f.getAttribute('action') || '')) continue;
          putHidden(f, '_entry_page', entry.p);
          putHidden(f, '_entry_ref', entry.r);
          putHidden(f, '_prev_page', prev);
          putHidden(f, '_src', mark.src || '');
          putHidden(f, '_utm', utmText());
        }
      } catch (err) { /* ignore */ }
    }

    // ---- 7e. 記事 → 市場ノートの「最新の数字」の札 ----
    // 需給調整市場・卸電気・容量市場を扱う記事（2026-11-21 に選んだ11本。英語は英語版のある物）
    var RP_COLS = ['/column-balancing-market', '/column-eprx', '/column-area-data', '/column-price-cap', '/column-balancing-saturation',
      '/column-bidding-ceiling-market', '/column-day-ahead', '/column-revenue', '/column-regional-revenue', '/column-merchant', '/column-capacity-market'];
    var RP_JA_ONLY = [];   // 英語版の無い記事（容量市場・前日取引化は英語版ができたので外した）
    var wantCard = isCol && ((isJa && RP_COLS.indexOf(loc) !== -1) || (isEn && RP_COLS.indexOf(loc) !== -1 && RP_JA_ONLY.indexOf(loc) === -1));
    var cardCss = [
      '.scix-rp-card{max-width:760px;margin:36px 0;padding:18px 22px 16px;background:#fff;border:1px solid #D6E9E0;border-left:6px solid #138A62;border-radius:18px;box-shadow:0 8px 22px rgba(31,42,72,.08);font-family:"Noto Sans JP",sans-serif;box-sizing:border-box;color:#0B1530}',
      '.scix-rp-card *{box-sizing:border-box}',
      '.scix-rp-label{display:inline-flex;font-size:.74rem;font-weight:900;color:#0F7A52;background:#E6F7EF;border-radius:999px;padding:3px 12px;margin:0 0 8px}',
      '.scix-rp-h{font-weight:900;font-size:1.02rem;line-height:1.5;margin:0 0 4px;color:#0B1530}',
      '.scix-rp-card ul.scix-rp-list{margin:6px 0 12px;padding:0 0 0 1.2em;list-style:disc;line-height:1.8;font-size:.9rem;color:#24304A}',
      '.scix-rp-card ul.scix-rp-list li{margin:4px 0;padding:0;background:none;border:0}',
      '.scix-rp-card ul.scix-rp-list li::before{content:none}',
      '.scix-rp-card a.scix-rp-go{display:inline-block;background:#138A62;color:#fff;font-weight:900;font-size:.9rem;padding:9px 18px;border-radius:999px;text-decoration:none;margin:4px 12px 4px 0;border:0}',
      '.scix-rp-card a.scix-rp-go:hover{background:#0F7A52;color:#fff}',
      '.scix-rp-card a.scix-rp-all{font-size:.86rem;color:#0F7A52;text-decoration:underline;border:0}',
      '@media(max-width:600px){.scix-rp-card{padding:16px 16px 14px;border-radius:16px}}'
    ].join('\n');
    function issueName(key, en) {
      var y = key.slice(0, 4), mo = parseInt(key.slice(5, 7), 10);
      var M = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
      return en ? (M[mo - 1] + ' ' + y + ' issue') : (y + '年' + mo + '月号');
    }
    function cardAnchor() {
      var ab = document.querySelector('.author-box');
      var hs = document.querySelectorAll('h2');
      for (var hi = 0; hi < hs.length; hi++) {
        var tx = (hs[hi].textContent || '').replace(/\s+/g, '');
        if (/^(よくある質問|FAQ|Frequentlyaskedquestions|FrequentlyAskedQuestions)/i.test(tx) &&
            (!ab || (hs[hi].compareDocumentPosition(ab) & 4))) return hs[hi];
      }
      return ab;
    }
    function placeCard(j) {
      try {
        var d = isEn ? j.en : j;
        if (!d || !d.eprx || !/^\/(en\/)?report\/\d{4}-\d{2}$/.test(d.url || '') || !/^\d{4}-\d{2}$/.test(j.key || '')) return;
        var at = cardAnchor();
        if (!at || !at.parentNode) return;
        var st = document.createElement('style');
        st.id = 'scix-rp-card-css';
        st.textContent = cardCss;
        document.head.appendChild(st);
        var box = document.createElement('aside');
        box.className = 'scix-rp-card';
        box.setAttribute('data-where', 'body_end');
        box.setAttribute('aria-label', isEn ? 'Latest figures from the Market Notes' : '市場ノートの最新の数字');
        var lb = document.createElement('div'); lb.className = 'scix-rp-label'; lb.textContent = isEn ? 'Market Notes' : '市場ノート';
        var h = document.createElement('div'); h.className = 'scix-rp-h';
        h.textContent = isEn ? ('Latest figures (' + issueName(j.key, true) + ')') : ('最新の数字（' + issueName(j.key, false) + '）');
        var ul = document.createElement('ul'); ul.className = 'scix-rp-list';
        var items = [d.eprx, d.jepx];
        for (var ii = 0; ii < items.length; ii++) {
          if (!items[ii]) continue;
          var li = document.createElement('li'); li.textContent = String(items[ii]).slice(0, 300); ul.appendChild(li);
        }
        var go = document.createElement('a'); go.className = 'scix-rp-go'; go.href = d.url; go.setAttribute('target', '_top');
        go.textContent = isEn ? ('Read the ' + issueName(j.key, true) + ' →') : (issueName(j.key, false) + 'を読む →');
        var all = document.createElement('a'); all.className = 'scix-rp-all'; all.href = isEn ? '/en/report' : '/report'; all.setAttribute('target', '_top');
        all.textContent = isEn ? 'All issues' : 'これまでの号';
        box.appendChild(lb); box.appendChild(h); box.appendChild(ul); box.appendChild(go); box.appendChild(all);
        at.parentNode.insertBefore(box, at);
        box.addEventListener('click', function (e) {
          var a = linkOf(e);
          if (!a || typeof window.gtag !== 'function') return;
          try {
            window.gtag('event', 'report_card_click', { page_path: path, link_url: a.getAttribute('href') || '', placement: 'body_end',
              page_lang: (document.documentElement.lang || lang), transport_type: 'beacon' });
          } catch (err) { /* ignore */ }
        });
      } catch (err) { /* 札を出せなくても頁はそのまま */ }
    }
    var cardData = null, domReady = document.readyState !== 'loading';
    function tryCard() { if (cardData && domReady) { placeCard(cardData); cardData = null; } }
    if (wantCard && window.fetch) {
      try {
        window.fetch('/report/latest.json', { credentials: 'omit' })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (j) { if (j && typeof j === 'object') { cardData = j; tryCard(); } })
          .catch(function () { /* 読めなければ札を出さない */ });
      } catch (err) { /* ignore */ }
    }

    function onReady() { domReady = true; fillForms(); tryCard(); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', onReady); else onReady();
  })(); } catch (err) { /* 測る仕組みが失敗しても頁はそのまま */ }

  // --------------- 6. 面談の予約について ---------------
  // 2026-09-05 撤去。Googleカレンダーの「予約スケジュール」は Google Meet のリンクを発行するため、
  // 「こちらが主催する会議は必ず Zoom」（2026-08-23 決定）に反する。
  // 面談は問い合わせへの返信で候補日時を出して決める。各ページの予約ボタンも同時に削除した。
  // 復活させるときは Zoom 側の予約ページを用意してからにする。

})();
