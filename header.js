(function () {
  /* ======================================================
     ScienceX — Shared Navigation Header (JP + EN + 简中)
     Single source of truth for all pages.

     2026-11-23: 上の帯を「ロゴ固定＋蓄電所マーケットのまとまり」に組み替えた（中島「サブメニューを押さないと展開しないのが動きが嫌だ」「サイエンスエックスのロゴは左上固定で変えずに…」「買いたい売りたいが他のメニューとならびすぎ…会社の主体は蓄電所マーケット」）。
       ・左上は ScienceX のロゴ（/img/logo-navy.png・高さ38px）で固定。蓄電所マーケット側の帯も同じ画像・同じ位置・同じ大きさにする（行き先は会社サイトのトップ・英語は /en）。
       ・ロゴのすぐ右に、角丸の1つの枠（.scix-mg）で「蓄電所マーケット」のまとまり: 印と名前（マーケットのトップへ）→ 買いたい → 売りたい。ほかの札より一段強い。
       ・細い区切りのあと、ナレッジ・市場リサーチ・会社案内・お問い合わせを一段軽く（普通の太さ・地色なし・絵なし）。
       ・引き出しのある札（買いたい・売りたい・ナレッジ・市場リサーチ）は、札そのものが頁へのリンク。マウス（hover あり・広い帯）は合わせると開き押すと頁へ、
         指と畳んだメニューは1回目の押下で開き（頁は移らない）2回目で頁へ、キーボードは Enter＝頁へ・↓＝開いて最初のリンクへ・Esc＝閉じる（3b）。割りボタン（▾ だけが開く形）は廃止。
       ・市場リサーチの札は入口の頁 /research（英語 /en/research）へ。中国語は入口の頁を作らず、今の札（市场研究＝英語の市場ノート）のまま。
       ・幅: 1600 以上は一回り大きく／1440 以上は外の札の余白を広げ／1359 以下はログインを人の印だけに／1199 以下は名前を枠の上の縁の見出し（12px）に／1100 以下は畳んだメニュー（一番上にまとまり）。蓄電所マーケットの帯（public/platform-nav.js・dr2.css）へ同じ値で写す。

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
    else if (path === '/zh-faq') loc = '/faq';
    else if (path === '/zh-market-data') loc = '/market-data';
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
    : /^\/(knowledge|column-|guide-|report|research|glossary|qa|faq|primer|market-entry|citation)/.test(loc) ? 'read'
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
    '/faq': { en: '/en/faq', zh: '/zh-faq' },
    '/market-data': { en: '/en/market-data', zh: '/zh-market-data' },
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
    '  font-family:"Noto Sans JP","Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP",-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif;',
    '  font-feature-settings:"palt" 1;',
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
    '/* 2026-11-23: 左から ロゴ → 蓄電所マーケットのまとまり（名前・買いたい・売りたい）→ 細い区切り → 読み物と会社の札。まとまりは角の丸い1つの枠で、中の札は一段強く、外の札は一段軽い。蓄電所マーケットの帯（dr2.css）にも同じ形・同じ値で写す */',
    '.scix-header-nav{--pc:#1F2A48;--fs:14.5px;--px:9px;display:flex;align-items:stretch;align-self:stretch;gap:0;margin-left:12px;margin-right:auto;min-width:0}',
    '.scix-header-nav > a,.scix-header-nav > .scix-nav-dd > .scix-nav-main{display:inline-flex;align-items:center;gap:6px;height:100%;padding:0 var(--px);color:#1F2A48;font-size:var(--fs);font-weight:500;line-height:1.3;text-decoration:none;white-space:nowrap;background:none;border:0;border-radius:0;cursor:pointer;font-family:inherit;transition:color .15s,background .15s,box-shadow .15s}',
    '.scix-ic{width:19px;height:19px;flex:0 0 auto;display:block;color:var(--pc)}',
    '.scix-nav-dd{position:relative;display:flex;align-items:center;--pc:#1F2A48}',
    '.scix-nav-dd[data-group=knowledge]{--pc:#7C4DDB}',
    '.scix-nav-dd[data-group=buy],.scix-mg a.scix-top-buy{--pc:#2563EB}',
    '.scix-nav-dd[data-group=sell],.scix-mg a.scix-top-sell{--pc:#C2560A}',
    '.scix-nav-dd[data-group=research],.scix-header-nav > a[data-page="/report"]{--pc:#138A62}',
    '.scix-header-nav > a:hover,.scix-header-nav > .scix-nav-dd > .scix-nav-main:hover,.scix-header-nav > .scix-nav-dd.open > .scix-nav-main{background:#F3F5FA;box-shadow:inset 0 -4px 0 var(--pc)}',
    '.scix-header-nav > a.active,.scix-header-nav > .scix-nav-dd > .scix-nav-main.active{color:var(--pc);font-weight:700;background:none;box-shadow:inset 0 -4px 0 var(--pc)}',
    '.scix-nav-sep{align-self:center;flex:0 0 auto;width:1px;height:28px;margin:0 6px 0 8px;background:#D5DCEA}',
    '/* 蓄電所マーケットのまとまり: 淡い地色と細い枠の1つの角丸の枠。中は 名前（マーケットのトップへ）→ 買いたい → 売りたい */',
    '.scix-mg{display:flex;align-items:center;align-self:center;gap:2px;flex:0 0 auto;position:relative;height:48px;padding:0 5px;background:#F3F6FD;border:1.5px solid #D2DCF2;border-radius:16px}',
    '.scix-mg-name{display:inline-flex;align-items:center;gap:7px;position:relative;height:100%;padding:0 11px 0 6px;color:#1F2A48;font-size:14px;font-weight:800;letter-spacing:.01em;line-height:1.2;text-decoration:none;white-space:nowrap}',
    '.scix-mg-name::after{content:"";position:absolute;right:0;top:50%;width:1px;height:24px;margin-top:-12px;background:#D2DCF2}',
    '.scix-mg-mark{width:25px;height:25px;flex:0 0 auto;display:block}',
    '.scix-mg-name:hover span{text-decoration:underline;text-underline-offset:3px}',
    '.scix-mg > .scix-nav-dd{height:38px}',
    '.scix-mg .scix-nav-main{display:inline-flex;align-items:center;gap:6px;height:38px;padding:0 8px 0 7px;color:#1F2A48;font-size:15.5px;font-weight:900;line-height:1.2;text-decoration:none;white-space:nowrap;background:none;border:0;border-radius:12px;cursor:pointer;font-family:inherit;transition:color .15s,background .15s,box-shadow .15s}',
    '.scix-mg .scix-ic{width:20px;height:20px}',
    '.scix-mg .scix-nav-main:hover,.scix-mg .scix-nav-dd.open > .scix-nav-main{background:#fff;box-shadow:inset 0 0 0 2px var(--pc),0 3px 10px rgba(31,42,72,.10)}',
    '.scix-mg .scix-nav-main.active{background:var(--pc);color:#fff;box-shadow:none}',
    '.scix-mg .scix-nav-main.active .scix-ic{color:#fff}',
    '/* 2026-11-22: ログイン・無料で登録は頁の案内の外（右端の1組）。ログインは枠だけの小さな丸、登録は橙の主ボタン */',
    '.scix-auth{display:flex;align-items:center;gap:10px;margin-left:16px;flex-shrink:0}',
    '.scix-auth-m{display:none}',
    '.scix-auth a.scix-login,.scix-auth-m a.scix-login{display:inline-flex;align-items:center;gap:6px;height:auto;padding:7px 14px 7px 11px;border:1.5px solid #C9D2E3;border-radius:999px;background:#fff;color:#1F2A48;font-size:14px;font-weight:700;line-height:1.3;text-decoration:none;white-space:nowrap;transition:border-color .15s,background .15s}',
    '.scix-auth a.scix-login svg,.scix-auth-m a.scix-login svg{width:18px;height:18px;flex:0 0 auto;display:block;color:#5B667A}',
    '.scix-auth a.scix-login:hover,.scix-auth-m a.scix-login:hover{border-color:#1F2A48;background:#F3F5FA}',
    '.scix-auth a.scix-mk,.scix-auth-m a.scix-mk{display:inline-flex;align-items:center;justify-content:center;height:auto;margin:0;padding:9px 18px;background:#C2560A;color:#fff;font-weight:900;font-size:15px;line-height:1.3;border-radius:999px;box-shadow:0 6px 16px rgba(194,86,10,.30);text-decoration:none;white-space:nowrap;transition:background .15s,box-shadow .15s,transform .15s}',
    '.scix-auth a.scix-mk:hover,.scix-auth-m a.scix-mk:hover{background:#B8520A;color:#fff;box-shadow:0 8px 20px rgba(194,86,10,.38);transform:translateY(-1px)}',
    '.scix-auth a:focus-visible,.scix-auth-m a:focus-visible{outline:2px solid #F97316;outline-offset:2px}',
    '.scix-en-tag{font-size:.66em;font-weight:800;color:#5B667A;border:1px solid #C9D2E3;border-radius:999px;padding:0 6px;margin-left:5px;line-height:1.6;white-space:nowrap}',
    '/* 外の札（ナレッジ・市場リサーチ・会社案内・お問い合わせ）は絵を付けない＝まとまりの中の札だけが絵つきで一段強い（畳んだメニューの中は絵を戻す） */',
    '.scix-header-nav > a .scix-ic,.scix-header-nav > .scix-nav-dd > .scix-nav-main .scix-ic{display:none}',
    '/* 幅ごとの値（広い→狭い）。基本は 1360px 前後の値／≥1600 は一回り大きく／≥1440 は外の札の余白を広げ／≤1359 はログインを人の印だけに／≤1299 は外の札の余白を詰め／≤1279 は買いたい・売りたいを詰め（1101〜1199 だけ名前を枠の上の縁の見出しにする） */',
    '@media(min-width:1101px){.scix-header-inner .scix-lang .scix-flag{width:23px;height:15px}.scix-header-inner .scix-lang{margin-left:10px}}',
    '@media(min-width:1440px){.scix-header-nav{--px:10px}.scix-mg-name{font-size:14.5px}.scix-mg .scix-nav-main{font-size:16px;padding:0 9px 0 8px}.scix-mg .scix-ic{width:22px;height:22px}.scix-header-inner .scix-lang .scix-flag{width:26px;height:17px}.scix-header-inner .scix-lang{margin-left:14px}}',
    '@media(min-width:1600px){.scix-header-nav{--fs:15px;--px:12px;margin-left:18px}.scix-nav-sep{margin:0 8px 0 10px}.scix-mg-name{font-size:14.5px;gap:8px;padding:0 13px 0 7px}.scix-mg-mark{width:27px;height:27px}.scix-mg .scix-nav-main{font-size:16.5px;gap:7px;padding:0 11px 0 10px}.scix-mg .scix-ic{width:23px;height:23px}}',
    '@media(min-width:1101px) and (max-width:1359px){.scix-auth a.scix-login{padding:8px 10px}.scix-auth a.scix-login span{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}.scix-auth{gap:8px;margin-left:10px}.scix-auth a.scix-mk{padding:9px 15px;font-size:14px}}',
    '@media(min-width:1101px) and (max-width:1299px){.scix-header-nav{--px:8px}}',
    '@media(min-width:1101px) and (max-width:1279px){.scix-header-nav{--fs:13.5px;--px:6px;margin-left:8px}.scix-nav-sep{margin:0 4px 0 6px}.scix-header.is-ja .scix-mg .scix-nav-main{font-size:15.5px;gap:6px;padding:0 8px 0 7px}.scix-header.is-ja .scix-mg .scix-ic{width:20px;height:20px}}',
    '/* 全言語とも 1200px から名前を枠の中に置き、1101〜1199 だけ枠の上の縁の見出し（12px・帯の中に収める）にする */',
    '@media(min-width:1101px) and (max-width:1199px){.scix-header .scix-mg-name{position:absolute;left:13px;top:-7px;height:auto;gap:5px;padding:0 6px;background:#fff;font-size:12px;font-weight:800;color:#3A4663}.scix-header .scix-mg-name::after{display:none}.scix-header .scix-mg-mark{width:15px;height:15px}.scix-header .scix-mg .scix-nav-main{font-size:15.5px;gap:6px;padding:0 8px 0 7px}.scix-header .scix-mg .scix-ic{width:20px;height:20px}}',
    '.scix-header-nav a:focus-visible,.scix-nav-dd-toggle:focus-visible,.scix-mg-name:focus-visible{outline:2px solid #F97316;outline-offset:2px}',

    '/* === Dropdown groups (買いたい / 売りたい / ナレッジ / 市場リサーチ) === */',
    '/* 2026-11-23: 引き出しのある札は全部「札そのものが頁へのリンク」＋合わせると開く（マウス）／1回目で開き2回目で頁へ（指・畳んだメニュー）。割りボタン（▾ だけが開く形）は作らない */',
    '.scix-nav-dd-toggle{display:inline-flex;align-items:center}',
    '.scix-dd-caret{font-size:.7em;transition:transform .25s;opacity:.85;margin-left:1px}',
    '.scix-nav-dd-menu{position:absolute;top:100%;left:0;min-width:224px;width:max-content;max-width:calc(100vw - 24px);background:#fff;border:0;border-radius:18px;padding:8px;display:none;flex-direction:column;gap:2px;box-shadow:0 18px 40px rgba(31,42,72,.18);z-index:10003}',
    '.scix-nav-dd.open > .scix-nav-dd-menu{display:flex}',
    '.scix-nav-dd.open .scix-dd-caret{transform:rotate(180deg)}',
    '.scix-mg .scix-nav-dd-menu{top:calc(100% + 14px)}',
    '/* 札と引き出しの間のすき間は、引き出しの一部の透明な橋でふさぐ（マウスを下ろす途中で閉じない） */',
    '.scix-nav-dd-menu::before{content:"";position:absolute;left:0;right:0;top:-16px;height:16px}',
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
    '@media(max-width:1380px){html[lang="en"] .scix-lang-label{display:none}html[lang="en"] .scix-lang a{padding:5px 7px;gap:0}}',
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
    '  .scix-header-nav{position:fixed;top:0;right:0;bottom:0;width:320px;max-width:86vw;background:#FFFCF5;border-radius:22px 0 0 22px;flex-direction:column;align-items:stretch;gap:0;padding:76px 18px 32px;transform:translateX(100%);transition:transform .35s cubic-bezier(.4,0,.2,1);z-index:10001;box-shadow:none;overflow-y:auto;margin:0}',
    '  .scix-header-open .scix-header-nav{transform:translateX(0);box-shadow:-4px 0 24px rgba(0,0,0,.15)}',   // 影は開いた時だけ（閉じた引き出しの影が画面の右の縁ににじんでいた）
    '  .scix-ic{display:block!important;width:21px;height:21px}',
    '  .scix-nav-sep{display:none}',
    '  /* 畳んだメニューの中: 一番上に「蓄電所マーケット」の見出しつきのまとまり（買いたい・売りたい）→ ログイン・無料で登録 → 読み物と会社の札 */',
    '  .scix-mg{display:block;align-self:stretch;height:auto;padding:10px 10px 8px;margin:0 0 14px;border-radius:20px}',
    '  .scix-mg-name{position:static;display:flex;height:auto;gap:8px;padding:2px 6px 10px;background:none;font-size:.9rem;font-weight:800;color:#1F2A48}',
    '  .scix-mg-name::after{display:none}',
    '  .scix-mg-mark{width:26px;height:26px}',
    '  .scix-mg > .scix-nav-dd{display:block;height:auto}',
    '  .scix-mg .scix-nav-main,.scix-mg > a.scix-nav-main{display:flex;width:100%;height:auto;padding:13px 12px;margin-top:6px;gap:9px;font-size:1.05rem;background:#fff;border:1.5px solid #E1E7F3;border-radius:14px;box-shadow:none}',
    '  .scix-mg .scix-ic{width:23px;height:23px}',
    '  .scix-mg .scix-nav-main:hover,.scix-mg .scix-nav-dd.open > .scix-nav-main{background:#fff;border-color:var(--pc);box-shadow:none}',
    '  .scix-mg .scix-nav-main.active{background:var(--pc);border-color:var(--pc)}',
    '  .scix-header-nav > a,.scix-header-nav > .scix-nav-dd > .scix-nav-main{display:flex;width:100%;height:auto;padding:14px 12px;font-size:.95rem;gap:8px;border-bottom:1px solid #EEE;border-radius:12px;box-shadow:none}',
    '  .scix-header-nav > a:hover,.scix-header-nav > a.active,.scix-header-nav > .scix-nav-dd > .scix-nav-main:hover,.scix-header-nav > .scix-nav-dd > .scix-nav-main.active,.scix-header-nav > .scix-nav-dd.open > .scix-nav-main{box-shadow:none;background:none}',
    '  .scix-auth{display:none}',
    '  .scix-auth-m{display:flex;flex-direction:column;gap:10px;padding:0 0 14px;margin-bottom:6px;border-bottom:1px solid #EEE}',
    '  .scix-auth-m a.scix-login{justify-content:center;padding:12px 20px;font-size:.95rem}',
    '  .scix-auth-m a.scix-mk{padding:13px 20px;font-size:.95rem}',
    '  .scix-nav-dd{flex-direction:column;align-items:stretch}',
    '  .scix-nav-dd-toggle .scix-dd-caret{margin-left:auto;font-size:.8em}',
    '  .scix-nav-dd-menu{position:static;display:none;border:none;box-shadow:none;background:#FFF1E3;padding:2px 0;min-width:0;width:auto;max-width:none;border-radius:14px;margin-top:4px}',
    '  .scix-mg .scix-nav-dd-menu{top:auto}',
    '  .scix-nav-dd-menu::before{display:none}',
    '  .scix-nav-dd.open > .scix-nav-dd-menu{display:flex}',
    '  .scix-nav-dd-menu a{padding:12px 12px 12px 28px;font-size:.88rem;border-bottom:1px solid rgba(31,42,72,.06);border-radius:0}',
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

  // --------------- 1b. 下の帯（footer.scix-footer を組み替えた形・2026-11-23） ---------------
  // 白地・上の縁に紺の2pxの線（上の帯の下の線の鏡）。上の帯の部品（まとまり・ログイン・登録・言葉の切り替え）と同じ値を、
  // 下の帯だけに効く名前（.scix-ft-*）で書く（上の帯の .scix-mg・.scix-ic・.scix-flag・.scix-lang は畳んだメニューの規則が全体に効くので使わない）。
  // 頁の <style> にある古い下の帯の規則（.scix-footer *{margin:0;padding:0} など）に負けないよう、footer.scix-ft から書く。
  var FT_FONT = '"Noto Sans JP","Hiragino Sans","Hiragino Kaku Gothic ProN",-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif';
  css += '\n' + [
    'footer.scix-footer.scix-ft{display:block!important;background:#fff!important;background-image:none!important;border:0!important;border-top:2px solid #1F2A48!important;border-radius:0!important;box-shadow:none!important;margin:56px 0 0!important;padding:0!important;width:auto!important;color:#24304A!important;font-family:' + FT_FONT + '!important;font-feature-settings:"palt" 1;font-size:14px!important;font-weight:400!important;line-height:1.6!important;letter-spacing:0!important;text-align:left!important}',
    'footer.scix-ft::before,footer.scix-ft::after{display:none!important}',
    'footer.scix-ft *,footer.scix-ft *::before,footer.scix-ft *::after{box-sizing:border-box}',
    'footer.scix-ft .scix-ft-in{max-width:none;margin:0;padding:34px 24px 22px}',   // 上の帯（.scix-header-inner）と同じ: 画面いっぱい・左右 24px（ロゴの左端と右端の部品が上下でそろう）
    'footer.scix-ft a{transition:color .15s,background .15s,border-color .15s,box-shadow .15s}',
    'footer.scix-ft a:focus-visible{outline:2px solid #F97316;outline-offset:2px}',
    '/* 1段目: ロゴ ／ 蓄電所マーケットのまとまり ／ ログイン・無料で登録 */',
    // 並べ方は上の帯と同じ: まとまりはロゴのすぐ右・ログインの組は margin-left:auto で右端（両端はそろう。space-between だとまとまりが真ん中に浮き、折り返すとばらばらになる）
    'footer.scix-ft .scix-ft-top{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-start;gap:16px 24px}',
    'footer.scix-ft .scix-ft-logo{display:flex;align-items:center;flex:0 0 auto;margin:0;padding:0;text-decoration:none}',
    'footer.scix-ft .scix-ft-logo img{display:block;height:38px;width:auto;margin:0}',
    'footer.scix-ft .scix-ft-mg{display:flex;align-items:center;gap:2px;flex:0 0 auto;height:48px;margin:0;padding:0 5px;background:#F3F6FD;border:1.5px solid #D2DCF2;border-radius:16px}',
    'footer.scix-ft .scix-ft-mg-name{display:inline-flex;align-items:center;gap:7px;position:relative;height:100%;margin:0;padding:0 11px 0 6px;color:#1F2A48;font-size:14px;font-weight:800;letter-spacing:.01em;line-height:1.2;text-decoration:none;white-space:nowrap}',
    'footer.scix-ft .scix-ft-mg-name::after{content:"";position:absolute;right:0;top:50%;width:1px;height:24px;margin-top:-12px;background:#D2DCF2}',
    'footer.scix-ft .scix-ft-mg-name:hover span{text-decoration:underline;text-underline-offset:3px}',
    'footer.scix-ft .scix-ft-mark{display:block;flex:0 0 auto;width:25px;height:25px}',
    'footer.scix-ft .scix-ft-side{--pc:#2563EB;display:inline-flex;align-items:center;gap:6px;height:38px;margin:0;padding:0 8px 0 7px;color:#1F2A48;font-size:15.5px;font-weight:900;line-height:1.2;text-decoration:none;white-space:nowrap;background:none;border:0;border-radius:12px}',
    'footer.scix-ft .scix-ft-side.is-sell{--pc:#C2560A}',
    'footer.scix-ft .scix-ft-side:hover{background:#fff;box-shadow:inset 0 0 0 2px var(--pc),0 3px 10px rgba(31,42,72,.10)}',
    'footer.scix-ft .scix-ft-ic{display:block;flex:0 0 auto;width:20px;height:20px;color:var(--pc)}',
    'footer.scix-ft .scix-ft-auth{display:flex;align-items:center;gap:10px;flex:0 0 auto;margin:0 0 0 auto}',
    'footer.scix-ft a.scix-ft-login{display:inline-flex;align-items:center;justify-content:center;gap:6px;margin:0;padding:7px 14px 7px 11px;border:1.5px solid #C9D2E3;border-radius:999px;background:#fff;color:#1F2A48;font-size:14px;font-weight:700;line-height:1.3;text-decoration:none;white-space:nowrap}',
    'footer.scix-ft a.scix-ft-login svg{display:block;flex:0 0 auto;width:18px;height:18px;color:#5B667A}',
    'footer.scix-ft a.scix-ft-login:hover{border-color:#1F2A48;background:#F3F5FA}',
    'footer.scix-ft a.scix-ft-reg{display:inline-flex;align-items:center;justify-content:center;margin:0;padding:9px 18px;background:#C2560A;color:#fff;font-size:15px;font-weight:900;line-height:1.3;border:0;border-radius:999px;box-shadow:0 6px 16px rgba(194,86,10,.30);text-decoration:none;white-space:nowrap}',
    'footer.scix-ft a.scix-ft-reg:hover{background:#B8520A;color:#fff;box-shadow:0 8px 20px rgba(194,86,10,.38);transform:translateY(-1px)}',
    '/* 2段目: 入口ごとの列（見出しは側の色の短い縦棒）。字の色は白地で 4.5:1 以上の濃さ（--tc） */',
    // 列の数は言葉ごとに違う（日本語 5・英語と中国語 3）。格子は列の数に合わせ、右に空いた列を残さない（n3・n4・n5）
    'footer.scix-ft .scix-ft-cols{display:grid;grid-template-columns:repeat(5,minmax(0,320px));justify-content:space-between;gap:8px 28px;margin:22px 0 0;padding:22px 0;border-top:1px solid #E3E8F2}',
    'footer.scix-ft .scix-ft-cols.n4{grid-template-columns:repeat(4,minmax(0,320px))}',
    'footer.scix-ft .scix-ft-cols.n3{grid-template-columns:repeat(3,minmax(0,320px))}',
    'footer.scix-ft .scix-ft-cols.n2{grid-template-columns:repeat(2,minmax(0,320px))}',
    'footer.scix-ft .scix-ft-col{--pc:#1F2A48;--tc:#1F2A48;min-width:0;margin:0;padding:0}',
    'footer.scix-ft .scix-ft-col.is-buy{--pc:#2563EB;--tc:#2563EB}',
    'footer.scix-ft .scix-ft-col.is-sell{--pc:#C2560A;--tc:#C2560A}',
    'footer.scix-ft .scix-ft-col.is-knowledge{--pc:#7C4DDB;--tc:#7C4DDB}',
    'footer.scix-ft .scix-ft-col.is-research{--pc:#138A62;--tc:#0F7A52}',
    // 列の見出しは h2（読み上げで見出しとして拾われる）。頁の h2 の飾り（線・地・字間・::after）が入らないよう全部ここで決める
    'footer.scix-ft .scix-ft-h{display:flex;align-items:center;gap:8px;margin:0 0 4px;padding:0;color:#1F2A48;font-family:inherit;font-size:13px;font-weight:900;line-height:1.5;letter-spacing:0;text-transform:none;text-align:left;background:none;border:0;box-shadow:none}',
    'footer.scix-ft .scix-ft-h::before{content:"";display:block;flex:0 0 auto;width:4px;height:14px;margin:0;border-radius:2px;background:var(--pc);position:static}',
    'footer.scix-ft .scix-ft-h::after{content:none;display:none}',
    // 見出しと同じ言葉の1本目（英語の Knowledge など）は見出しそのものをリンクにして、同じ言葉を2つ並べない
    'footer.scix-ft .scix-ft-col .scix-ft-h a{display:inline;margin:0;padding:0;color:inherit;font:inherit;text-decoration:none;border:0;background:none}',
    'footer.scix-ft .scix-ft-col .scix-ft-h a:hover{color:var(--tc);text-decoration:underline;text-underline-offset:3px}',
    'footer.scix-ft .scix-ft-col ul{list-style:none;margin:0;padding:0}',
    'footer.scix-ft .scix-ft-col li{list-style:none;margin:0;padding:0;background:none;border:0}',
    'footer.scix-ft .scix-ft-col li::before{content:none}',
    // 長い札（系統用蓄電池の売り案件 市場データ など）は語の切れ目（空白）で折り、最後の1字だけが次の行に残らないようにする（入りきらない時だけ語の中で折る）
    'footer.scix-ft .scix-ft-col a{display:inline-block;margin:0;padding:5px 0;color:#24304A;font-size:14px;font-weight:500;line-height:1.5;text-decoration:none;border:0;background:none;word-break:keep-all;overflow-wrap:anywhere;text-wrap:balance}',
    'footer.scix-ft .scix-ft-col a:hover{color:var(--tc);text-decoration:underline;text-underline-offset:3px}',
    '/* 3段目: 会社の行（社名・住所・TEL・MAIL・代表者）と言葉の切り替え ／ 4段目: 著作権 */',
    'footer.scix-ft .scix-ft-co{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px 24px;margin:0;padding:18px 0 0;border-top:1px solid #E3E8F2}',
    '/* 区切りの細い縦線は各項目の左に置き、行の頭に来た線は枠の外（overflow:hidden）に隠す */',
    'footer.scix-ft .scix-ft-info{flex:1 1 520px;min-width:0;margin:0;padding:0;overflow:hidden;color:#4A5568;font-size:13px;line-height:1.85}',
    'footer.scix-ft .scix-ft-info-in{display:flex;flex-wrap:wrap;align-items:baseline;margin:0 0 0 -21px}',
    'footer.scix-ft .scix-ft-seg{position:relative;flex:0 0 auto;padding-left:21px;white-space:nowrap}',
    'footer.scix-ft .scix-ft-seg.is-addr{flex:0 1 auto;min-width:0;white-space:normal}',
    'footer.scix-ft .scix-ft-seg::before{content:"";position:absolute;left:10px;top:50%;width:1px;height:12px;margin-top:-6px;background:#C9D2E3}',
    'footer.scix-ft .scix-ft-name{color:#1F2A48;font-size:14px;font-weight:900}',
    'footer.scix-ft .scix-ft-info a{color:#1F2A48;font-weight:700;text-decoration:none;border:0}',
    'footer.scix-ft .scix-ft-info a:hover{text-decoration:underline;text-underline-offset:3px}',
    'footer.scix-ft .scix-ft-lang{display:flex;align-items:center;gap:3px;flex:0 0 auto;margin:0;padding:3px;border:2px solid #1F2A48;border-radius:100px;background:#fff}',
    'footer.scix-ft .scix-ft-lang a{display:inline-flex;align-items:center;margin:0;padding:5px 7px;border-radius:100px;color:#1F2A48;line-height:1.3;text-decoration:none}',
    'footer.scix-ft .scix-ft-lang a:hover{background:#E9EBF1}',
    'footer.scix-ft .scix-ft-lang a.active{background:#1F2A48}',
    'footer.scix-ft .scix-ft-flag{display:block;flex-shrink:0;width:26px;height:17px;border-radius:3px;box-shadow:0 0 0 1px rgba(0,0,0,.18)}',
    'footer.scix-ft .scix-ft-lang a.active .scix-ft-flag{box-shadow:0 0 0 2px #fff}',
    'footer.scix-ft .scix-ft-copy{margin:14px 0 0;padding:0;color:#6B7280;font-size:12px;line-height:1.6}',
    // 免責の段（/fund・/grid-storage の頁の下の帯にあった物）: 下の帯の上に、本文と同じ幅で置く
    '.scix-ft-disc{box-sizing:border-box;max-width:1240px;margin:56px auto 0;padding:0 24px;color:#4A5568;font-family:' + FT_FONT + ';font-size:12px;line-height:1.8;text-align:left}',
    '.scix-ft-disc-in{padding:16px 18px;background:#fff;border:1px solid #E3E8F2;border-left:3px solid #D2DCF2;border-radius:0 10px 10px 0}',
    '.scix-ft-disc .scix-ft-disc-h{margin:0 0 6px;padding:0;color:#1F2A48;font-size:12.5px;font-weight:900}',
    '.scix-ft-disc p{margin:0 0 6px;padding:0;color:#4A5568}',
    '.scix-ft-disc p:last-child{margin-bottom:0}',
    '.scix-ft-disc + footer.scix-ft{margin-top:28px!important}',
    '@media(max-width:768px){.scix-ft-disc{padding:0 16px}}',
    // 1440px 以上は上の帯が一回り大きくなるので、同じ部品の大きさをそろえる（上の帯の 1440・1600 の段と同じ値）
    '@media(min-width:1440px){footer.scix-ft .scix-ft-mg-name{font-size:14.5px}footer.scix-ft .scix-ft-side{font-size:16px;padding:0 9px 0 8px}footer.scix-ft .scix-ft-ic{width:22px;height:22px}}',
    '@media(min-width:1600px){footer.scix-ft .scix-ft-mg-name{gap:8px;padding:0 13px 0 7px}footer.scix-ft .scix-ft-mark{width:27px;height:27px}footer.scix-ft .scix-ft-side{font-size:16.5px;gap:7px;padding:0 11px 0 10px}footer.scix-ft .scix-ft-ic{width:23px;height:23px}}',
    // 印刷では、押す部品（ログイン・登録・言葉の切り替え）を出さない
    '@media print{footer.scix-ft .scix-ft-auth,footer.scix-ft .scix-ft-lang{display:none!important}}',
    '/* 721〜1100px: 1段目は折り返してよい・列は3列 */',
    '/* 721〜900px: 1段目が1行に収まるよう、上の帯の 1101〜1359px と同じく「ログイン」は人の絵だけにし（読み上げには言葉を残す）、間を詰める */',
    '@media(min-width:721px) and (max-width:900px){footer.scix-ft .scix-ft-top{column-gap:16px}footer.scix-ft a.scix-ft-login{padding:8px 10px}footer.scix-ft a.scix-ft-login span{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}footer.scix-ft .scix-ft-auth{gap:8px}}',
    '@media(max-width:1100px){footer.scix-ft .scix-ft-cols{row-gap:18px}footer.scix-ft .scix-ft-cols.n5,footer.scix-ft .scix-ft-cols.n4{grid-template-columns:repeat(3,minmax(0,1fr))}}',
    '/* 〜768px: 右下の浮いた橙のボタン（.scix-float-cta）に最後の行が隠れないよう下を空ける。左右は本文と同じ 16px */',
    '@media(max-width:768px){footer.scix-ft .scix-ft-in{padding:30px 16px 88px}}',
    '/* 〜720px: 1段目は縦積み（ロゴ → まとまり〔畳んだメニューの中と同じ形〕→ ログイン・無料で登録）・列は2列・会社の行も縦積み */',
    '@media(max-width:720px){',
    '  footer.scix-ft .scix-ft-top{flex-direction:column;align-items:stretch;gap:16px}',
    '  footer.scix-ft .scix-ft-logo{align-self:flex-start}',
    '  footer.scix-ft .scix-ft-mg{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;height:auto;padding:10px;border-radius:20px}',
    '  footer.scix-ft .scix-ft-mg-name{grid-column:1/-1;height:auto;gap:8px;padding:2px 6px 2px;font-size:.9rem}',
    '  footer.scix-ft .scix-ft-mg-name::after{display:none}',
    '  footer.scix-ft .scix-ft-mark{width:26px;height:26px}',
    '  footer.scix-ft .scix-ft-side{justify-content:center;min-width:0;height:auto;padding:12px 8px;gap:8px;font-size:1rem;background:#fff;border:1.5px solid #E1E7F3;border-radius:14px}',
    '  footer.scix-ft .scix-ft-side:hover{border-color:var(--pc);box-shadow:none}',
    '  footer.scix-ft .scix-ft-auth{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:0}',
    '  footer.scix-ft a.scix-ft-login,footer.scix-ft a.scix-ft-reg{min-width:0;padding:11px 10px;font-size:14px}',
    '  footer.scix-ft .scix-ft-cols,footer.scix-ft .scix-ft-cols.n5,footer.scix-ft .scix-ft-cols.n4,footer.scix-ft .scix-ft-cols.n3{grid-template-columns:repeat(2,minmax(0,1fr));gap:18px 16px}',
    '  footer.scix-ft .scix-ft-co{flex-direction:column;align-items:flex-start}',
    '  footer.scix-ft .scix-ft-info{flex:0 1 auto}',
    '  footer.scix-ft .scix-ft-info-in{display:block;margin:0}',
    '  footer.scix-ft .scix-ft-seg,footer.scix-ft .scix-ft-seg.is-addr{display:block;padding:0;white-space:normal}',
    '  footer.scix-ft .scix-ft-seg::before{display:none}',
    '}'
  ].join('\n');

  // Floating mobile contact CTA — on mobile the nav collapses into the hamburger,
  // so keep a persistent, always-visible conversion path. white-on-black = WCAG AAA.
  css += "\n.scix-float-cta{position:fixed;right:16px;bottom:16px;z-index:9000;display:none;align-items:center;gap:7px;padding:13px 20px;background:linear-gradient(135deg,#C2560A,#B45309);color:#fff;font-family:'Noto Sans JP',sans-serif;font-size:14px;font-weight:900;text-decoration:none;border-radius:999px;box-shadow:0 8px 22px rgba(234,88,12,.38)}.scix-float-cta:active{transform:translateY(1px)}.scix-float-cta svg{width:16px;height:16px}@media(max-width:768px){.scix-float-cta{display:inline-flex;opacity:0;transform:translateY(16px);pointer-events:none;transition:opacity .2s,transform .2s}.scix-float-cta.on{opacity:1;transform:none;pointer-events:auto}}";

  // 中国語の頁の上の帯・下の帯は簡体字の書体を先頭に（前は Noto Sans JP が先頭で、JP に無い簡体字だけ別の書体に落ち、「购买」は細く「出售」は太く混ざった・2026-11-23）
  var ZH_FONT = '"Noto Sans SC","PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans JP",sans-serif';
  css += '\nhtml[lang^=zh] .scix-header,html[lang^=zh] footer.scix-footer.scix-ft,html[lang^=zh] .scix-ft-disc{font-family:' + ZH_FONT + '!important}' +
    'html[lang^=zh] .scix-dd-head{font-family:"Inter Tight",' + ZH_FONT + '}';
  // 〜1100px の言葉の切り替え（国旗だけ・見た目は高さ 26px のまま）: 押せる所を上下に広げて 38px に（2026-11-23）
  css += '\n@media(max-width:' + BP + 'px){.scix-lang a{position:relative}.scix-lang a::after{content:"";position:absolute;left:0;right:0;top:-6px;bottom:-6px}}';
  // 中国語の頁で Noto Sans SC を読んでいない頁（zh-faq・zh-glossary・zh-qa）には、帯の字のためにここで読む
  if (isZh && !document.querySelector('link[href*="Noto+Sans+SC"]')) {
    var scLink = document.createElement('link');
    scLink.rel = 'stylesheet';
    scLink.href = 'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;800;900&display=swap';
    document.head.appendChild(scLink);
  }

  // 2026-11-23 ログインの持ち越し（中島「サイエンスのTOPに行くとログアウトする仕様はおかしい。ログインしたままにして。」・中身は下の 2b）:
  // 蓄電所マーケットにログイン中の人は、上の帯・畳んだメニュー・下の帯の「ログイン」「無料で登録」を、人の印（頭文字）と名前・ログアウトに替える。
  // 印（localStorage）がある間（data-mkt-signed="guess"）は「ログイン」「無料で登録」を見えなくし（幅は保つ）、答えで決め直す。登録を促す一行（.hm-pr）と一覧の帯（tr.pj-band）はログイン中は出さない。
  css += '\nhtml[data-mkt-signed="guess"] .scix-auth>a,html[data-mkt-signed="guess"] .scix-auth-m>a,html[data-mkt-signed="guess"] .scix-ft-auth>a{visibility:hidden}' +
    'html[data-mkt-signed] .hm-pr,html[data-mkt-signed] tr.pj-band{display:none!important}' +
    '.scix-in{align-items:center;gap:8px}' +   // display は元の組の物のまま（広い帯は .scix-auth・畳んだメニューは .scix-auth-m だけが見える）
    '.scix-in span.scix-me{display:inline-flex;align-items:center;gap:8px;max-width:220px;padding:5px 14px 5px 5px;border:1.5px solid #C9D2E3;border-radius:999px;background:#fff;color:#1F2A48;font-size:14px;font-weight:700;line-height:1.3;white-space:nowrap}' +
    '.scix-in .scix-av{display:grid;place-items:center;flex:0 0 auto;width:28px;height:28px;border-radius:50%;background:#1F2A48;color:#F2C14E;font-size:13px;font-weight:800;line-height:1}' +
    '.scix-in .scix-av svg{width:17px;height:17px;color:#F2C14E}' +
    '.scix-in .scix-un{overflow:hidden;text-overflow:ellipsis;min-width:0}' +
    '.scix-in button.scix-out{flex:0 0 auto;margin:0;padding:7px 12px;border:0;border-radius:999px;background:none;color:#5B667A;font:inherit;font-size:13px;font-weight:700;line-height:1.3;white-space:nowrap;cursor:pointer}' +
    '.scix-in button.scix-out:hover{background:#F3F5FA;color:#1F2A48}' +
    '.scix-in button:focus-visible{outline:2px solid #F97316;outline-offset:2px}' +
    '.scix-in button.scix-out[disabled]{opacity:.5;cursor:default}' +
    '@media(min-width:1101px) and (max-width:1359px){.scix-auth.scix-in span.scix-me{padding:5px}.scix-auth.scix-in .scix-un{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}.scix-auth.scix-in{gap:4px}}' +
    '@media(max-width:' + BP + 'px){.scix-auth-m.scix-in{flex-direction:row;justify-content:space-between}.scix-auth-m.scix-in span.scix-me{flex:1 1 auto;max-width:none;padding:7px 16px 7px 7px;font-size:.95rem}}' +
    'footer.scix-ft .scix-ft-auth.scix-in{display:flex}' +
    '@media(max-width:720px){footer.scix-ft .scix-ft-auth.scix-in{display:flex;justify-content:space-between}footer.scix-ft .scix-ft-auth.scix-in span.scix-me{flex:1 1 auto;max-width:none}}' +
    '@media print{.scix-in{display:none!important}}';

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
  // 引き出しのある札（2026-11-23）: 札（a）そのものが行き先の頁へのリンク。
  //   マウス（hover のできる端末・広い帯）＝合わせると開き、押すと頁へ行く／指・畳んだメニュー＝1回目の押下で開き（頁は移らない）、開いている札をもう一度押すと頁へ行く。
  //   キーボード＝Enter は頁へ・↓ で開いて最初のリンクへ・Esc で閉じる（動きは下の 3b）。
  //   買いたい・売りたい・ナレッジ・市場リサーチの全部が同じ形（割りボタン〔▾ だけが開く形〕は作らない）。
  function ddNav(key, label, href, items, icon) {
    var wide = !!(items.length && items[0] && items[0].items);
    var out = '<div class="scix-nav-dd" data-group="' + key + '">' +
      '<a class="scix-nav-main scix-nav-dd-toggle" href="' + href + '" aria-haspopup="true" aria-expanded="false" aria-controls="scix-dd-' + key + '">' +
        (icon ? ic(icon) : '') + '<span>' + label + '</span><span class="scix-dd-caret" aria-hidden="true">▾</span>' +
      '</a>' +
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
    buy:   ['/projects', '/transfer', '/fund', '/investors', '/for/sme', '/for/major', '/market-data'],
    sell:  ['/sourcing', '/sell-form', '/partners', '/for/dealers'],
    research: ['/research', '/report']   // 2026-11-23: 市場の頁は速報（/report/flash）と月号（/report/<月>）の2本だけ。売り案件の市場データは「買いたい」へ戻した
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
  // 2026-11-23 中島「左上がサイエンスエックスのロゴのときと蓄電所マーケットのロゴの時がある。…サイエンスエックスのロゴは左上固定で変えずに、蓄電所マーケットのロゴは位置が違うんじゃないの？」
  //   「この買いたい売りたいってなんか他のメニューとならびすぎだよね。ここって蓄電所マーケットだよね。ただ、わけないほうがいいか。会社の主体は蓄電所マーケットなんだから」
  // 左上は両サイトとも ScienceX のロゴで固定。ロゴのすぐ右に「蓄電所マーケット」のまとまり（印と名前 → 買いたい → 売りたい・1つの角丸の枠）を置き、枠の外に、ナレッジ・市場リサーチ・会社案内・お問い合わせを一段軽く並べる（帯は1本のまま）。
  // 印は蓄電所マーケットの帯の左上にある物と同じ絵（scix-dealroom2 の functions/_lib/open_render.ts の MARK_SVG）。名前はマーケットのトップへのリンク。
  var MG_MARK = '<svg class="scix-mg-mark" viewBox="0 0 40 40" aria-hidden="true" focusable="false"><rect x="1" y="1" width="38" height="38" rx="11" fill="#1E3A8A"/><rect x="8.5" y="13" width="19.5" height="14" rx="3" fill="none" stroke="#fff" stroke-width="2.6"/><rect x="28" y="17.4" width="3.2" height="5.2" rx="1.2" fill="#fff"/><path d="M12.4 20.6h3.1l1.7-3.3 2.6 6.4 1.7-3.1h2.9" fill="none" stroke="#FBBF24" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var MG = isZh ? { name: '蓄电所市场', href: MKT + '/en', title: '前往蓄电所市场（英文页）' }
         : isEn ? { name: 'Chikudensho Market', href: MKT + '/en', title: 'Go to Chikudensho Market' }
         : { name: '蓄電所マーケット', href: MKT + '/', title: '蓄電所マーケットのトップへ' };
  function mgroup(inner) {
    return '<div class="scix-mg" role="group" aria-label="' + MG.name + '">' +
      '<a class="scix-mg-name" href="' + MG.href + '" data-k="market" title="' + MG.title + '">' + MG_MARK + '<span>' + MG.name + '</span></a>' +
      inner + '</div>';
  }
  var SEP = '<span class="scix-nav-sep" aria-hidden="true"></span>';
  var nav = isZh ? [
    mgroup(
      '<a href="' + MKT + '/en" class="scix-nav-main scix-top-buy" data-k="buy">' + ic('buy') + '<span>购买</span></a>' +
      '<a href="' + MKT + '/en/needs" class="scix-nav-main scix-top-sell" data-k="sell">' + ic('sell') + '<span>出售</span></a>'
    ),
    SEP,
    ddNav('knowledge', '洞见', '/zh-knowledge', [
      ['/zh-knowledge', '洞见', '', '/knowledge'],
      ['/zh-qa',        '问答', '', '/qa']
    ], 'book'),
    '<a href="/en/report" data-page="/report">' + ic('chart') + '<span>市场研究</span>' + EN_TAG + '</a>',
    '<a href="/zh-company" data-page="/company">' + ic('co') + '<span>公司介绍</span></a>',
    '<a href="/zh-contact" data-page="/contact">' + ic('mail') + '<span>联系我们</span></a>'
  ] : isEn ? [
    mgroup(
      '<a href="' + MKT + '/en" class="scix-nav-main scix-top-buy" data-k="buy">' + ic('buy') + '<span>Buy</span></a>' +
      '<a href="' + MKT + '/en/needs" class="scix-nav-main scix-top-sell" data-k="sell">' + ic('sell') + '<span>Sell</span></a>'
    ),
    SEP,
    ddNav('knowledge', 'Knowledge', '/en/knowledge', [
      ['/en/knowledge',          'Knowledge',   '', '/knowledge'],
      ['/en/qa',                 'Q&amp;A',     '', '/qa'],
      ['/en/market-entry-guide', 'Entry Guide', '', '/market-entry-guide']
    ], 'book'),
    ddNav('research', 'Market Research', '/en/research', [
      ['/en/report/flash', 'Market Notes: Daily Flash', '', '/report/flash'],
      ['/en/report',       'Market Notes: Monthly Issue (on the 1st)', '', '/report']
    ], 'chart'),
    '<a href="/en/company" data-page="/company">' + ic('co') + '<span>Company</span></a>',
    '<a href="/en/contact" data-page="/contact">' + ic('mail') + '<span>Contact</span></a>'
  ] : [
    // 2026-11-23 中島「メニュー多いのは良くない。シンプルに。」（共通ルール O16-72）: 買いたいは引き出し無しでマーケットの一覧へ直行。
    // 売りたいの引き出しは2つ（マーケットに自分で出す・当社に査定）。外した行き先（/transfer・/fund・/investors・/sourcing・/partners・/market-data ほか）は下の帯の列に。
    mgroup(
      '<a href="' + MKT + '/" class="scix-nav-main scix-top-buy" data-k="buy">' + ic('buy') + '<span>買いたい</span></a>' +
      ddNav('sell', '売りたい', MKT + '/needs', [
      [MKT + '/start/sell', '蓄電所を出す（無料）'],
      ['/sell-form',        '当社に無料で売却査定']
    ], 'sell')
    ),
    SEP,
    // 2026-11-23: ナレッジの引き出しは3つ（分野の5つは記事の頁のタブにある・そもそも／しくみは下の帯へ）
    ddNav('knowledge', 'ナレッジ', '/knowledge', [
      ['/knowledge', 'すべての記事（毎週更新）', 'scix-dd-all'],
      ['/qa',        '入門Q&amp;A（24問）'],
      ['/glossary',  '用語集']
    ], 'book'),
    // 市場リサーチ: 札そのものは入口の頁 /research へ（2026-11-23）。引き出しの中の札は、行き先の h1 と同じ言葉（O16-27）。
    // 2026-11-23 中島「メニュー多いのは良くない。シンプルに。速報で毎日の最新データ。毎月１日の前月最新データがいい。」＝引き出しは速報と月号の2つだけ。
    // 号をまたいだ推移（/report/data）は速報・月号の頁の中から、売り案件の市場データ（/market-data）は「買いたい」の引き出しへ。
    ddNav('research', '市場リサーチ', '/research', [
      ['/report/flash', '市場ノート 速報（毎日更新）'],
      ['/report',       '市場ノート 月号（毎月1日）']
    ], 'chart'),
    '<a href="/company"  data-page="/company">' + ic('co') + '<span>会社案内</span></a>',
    '<a href="/contact"  data-page="/contact">' + ic('mail') + '<span>お問い合わせ</span></a>'
  ];

  // 2026-11-22: ログイン・無料で登録は頁の案内ではなく利用者の操作なので、メニューの並びから外し、右端（言語の切り替えの手前）に隣り合わせで置く。
  // 広い画面は帯の右端の1組（.scix-auth）、畳んだメニューは開いた中の一番上の1組（.scix-auth-m）。同じ組を2か所に描いて、画面の幅でどちらかだけ見せる。
  var AUTH_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true" focusable="false"><circle cx="12" cy="8" r="3.6"/><path d="M5 20c.8-3.6 3.6-5.4 7-5.4s6.2 1.8 7 5.4"/></svg>';
  var AUTH = isZh ? { login: MKT + '/en/login', reg: MKT + '/en/register', lt: '登录', rt: '免费注册' }
           : isEn ? { login: MKT + '/en/login', reg: MKT + '/en/register', lt: 'Log in', rt: 'Sign up free' }
           : { login: MKT + '/login', reg: MKT + '/register', lt: 'ログイン', rt: '無料で登録' };
  function authHtml(cls) {
    return '<div class="' + cls + '">' +
      '<a href="' + AUTH.login + '" class="scix-login">' + AUTH_ICON + '<span>' + AUTH.lt + '</span></a>' +
      '<a href="' + AUTH.reg + '" class="scix-mk scix-reg">' + AUTH.rt + '</a></div>';
  }

  // --------------- 2b. ログインの持ち越し（2026-11-23） ---------------
  // 中島「サイエンスのTOPに行くとログアウトする仕様はおかしい。ログインしたままにして。」（同じ日「ログインしているのに価格見えないおかしい。ヘッダーではログイン・中身ではログインしろ」）
  // www.scix.co.jp と dealroom.scix.co.jp は同じサイト（scix.co.jp）なので、マーケットのログインの札（SameSite=Lax・host-only・HttpOnly）は
  // マーケットの口への fetch(…, { credentials: 'include' }) に付く。マーケットは https://www.scix.co.jp・https://scix.co.jp にだけ資格つきの CORS を返す
  // （scix-dealroom2 の functions/_lib/site_session.ts・/api/site/session＝名前と頭文字だけ・/api/site/prices＝トップのカードの価格）。
  // ・頁の HTML はログインの有無で同じ。出し分けはここ（と site-cards.js）だけ。答えが無い・失敗したらログインなしの形のまま。
  // ・印は localStorage の scix.mkt.signed（この住所の物・マーケットの dr2.signed とは別）。印があれば最初から「ログイン」「無料で登録」を見えなくし（data-mkt-signed="guess"）、答えで決め直す。
  // ・名前は textContent だけで入れる（innerHTML に入れない）。人の印はリンクにしない（マーケットの帯の印と同じ・マーケットへの入口は左の「蓄電所マーケット」のまとまり＝行き先を帯の中で重ねない）＝GA4 の nav_click に名前は乗らない。
  // ・www と apex 以外（invest.scix.co.jp・プレビューの住所）はマーケットが許していないので聞かない（手元の試しの localhost・127.0.0.1 だけ聞く＝許されず失敗→ログインなしの形）。
  var MKT_IN_KEY = 'scix.mkt.signed';
  var MKT_CARRY = /^(?:www\.scix\.co\.jp|scix\.co\.jp|localhost|127\.0\.0\.1)$/.test(location.hostname) && typeof fetch === 'function' && typeof Promise === 'function';
  var AUTH_IN = isZh ? { out: '退出登录', you: '已登录蓄电所市场' }
              : isEn ? { out: 'Log out', you: 'Signed in to Chikudensho Market' }
              : { out: 'ログアウト', you: '蓄電所マーケットにログイン中' };
  var MKT_ME = null;   // ログイン中と分かった時の { initial, name }
  function mktSetIn(on) { try { if (on) localStorage.setItem(MKT_IN_KEY, '1'); else localStorage.removeItem(MKT_IN_KEY); } catch (e) { /* 印を持てなくても動く */ } }
  function mktUnguess() { if (document.documentElement.getAttribute('data-mkt-signed') === 'guess') document.documentElement.removeAttribute('data-mkt-signed'); }
  if (MKT_CARRY) {
    try {
      if (localStorage.getItem(MKT_IN_KEY) === '1') {
        document.documentElement.setAttribute('data-mkt-signed', 'guess');
        setTimeout(mktUnguess, 4000);   // 答えが来なければログインなしの形に戻す
      }
    } catch (e) { /* 印が読めなければログインなしの形のまま */ }
  }
  // ログイン中の形の1組（.scix-auth・.scix-auth-m・.scix-ft-auth のどれか）。名前と頭文字は textContent で入れる
  function authInEl(cls) {
    var d = document.createElement('div');
    d.className = cls + ' scix-in';
    d.innerHTML = '<span class="scix-me" title="' + AUTH_IN.you + '"><span class="scix-av" aria-hidden="true"></span><span class="scix-un"></span></span>' +
      '<button type="button" class="scix-out" data-act="mkt-logout">' + AUTH_IN.out + '</button>';
    var av = d.querySelector('.scix-av'), un = d.querySelector('.scix-un');
    if (MKT_ME && MKT_ME.initial) av.textContent = MKT_ME.initial; else av.innerHTML = AUTH_ICON;
    un.textContent = (MKT_ME && MKT_ME.name) || (isEn ? 'Signed in' : isZh ? '已登录' : 'ログイン中');
    return d;
  }
  // root の中の「ログイン」「無料で登録」の組を、ログイン中の形に替える（もう替えた組は触らない）
  function mktPaint(root) {
    if (!MKT_ME || !root || !root.querySelectorAll) return;
    var els = root.querySelectorAll('.scix-auth:not(.scix-in), .scix-auth-m:not(.scix-in), .scix-ft-auth:not(.scix-in)');
    for (var i = 0; i < els.length; i++) {
      var cls = els[i].classList.contains('scix-auth-m') ? 'scix-auth-m' : els[i].classList.contains('scix-ft-auth') ? 'scix-ft-auth' : 'scix-auth';
      els[i].parentNode.replaceChild(authInEl(cls), els[i]);
    }
  }
  // 頁の中の「無料登録」の誘い（マーケットの /register・/en/register へのリンク）の字を、ログイン中の言い方に替える（行き先はそのまま＝マーケットが next か入口へ送る）
  var MKT_CTA_RULES = [
    [/（[^（）]*無料登録[^（）]*）/g, ''],
    [/無料登録して価格と資料を見る/g, '蓄電所マーケットで価格と資料を見る'],
    [/蓄電所マーケットに無料登録(?:する)?/g, '蓄電所マーケットを開く'],
    [/無料で登録/g, '蓄電所マーケットへ'],
    [/\s*\(free registration\)/gi, ''],
    [/Register free to see prices and documents?/g, 'See prices and documents'],
    [/Register (?:on|for) Chikudensho Market/g, 'Open Chikudensho Market'],
    [/Sign up free/g, 'Go to Chikudensho Market'],
    [/免费注册蓄电所市场/g, '打开蓄电所市场']
  ];
  function mktCtaText() {
    if (!MKT_ME || !document.body) return;
    var as = document.querySelectorAll('a[href*="/register"]');
    for (var i = 0; i < as.length; i++) {
      if (as[i].getAttribute('data-mkt-in')) continue;
      var u = null;
      try { u = new URL(as[i].getAttribute('href') || '', window.location.href); } catch (err) { u = null; }
      if (!u || !(u.hostname === 'dealroom.scix.co.jp' || u.origin === MKT) || !/^\/(?:en\/)?register$/.test(u.pathname)) continue;
      as[i].setAttribute('data-mkt-in', '1');
      var w = document.createTreeWalker(as[i], NodeFilter.SHOW_TEXT, null, false), n;
      while ((n = w.nextNode())) {
        var t = n.nodeValue, t2 = t;
        for (var r = 0; r < MKT_CTA_RULES.length; r++) t2 = t2.replace(MKT_CTA_RULES[r][0], MKT_CTA_RULES[r][1]);
        if (t2 !== t) n.nodeValue = t2;
      }
    }
  }
  function mktSignedIn(me) {
    MKT_ME = { initial: Array.from(String(me.initial || '')).slice(0, 1).join(''), name: Array.from(String(me.name || '')).slice(0, 40).join('') };
    document.documentElement.setAttribute('data-mkt-signed', '1');
    mktSetIn(true);
    mktPaint(document);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { mktPaint(document); mktCtaText(); });
    else mktCtaText();
  }
  // マーケットに聞く（3.5秒で打ち切り）。答えは site-cards.js も使う（window.SCIX_MKT_SESSION＝{ initial, name } か null の Promise）
  window.SCIX_MKT_SESSION = !MKT_CARRY ? (typeof Promise === 'function' ? Promise.resolve(null) : null) : new Promise(function (resolve) {
    var done = false;
    function fin(v) { if (done) return; done = true; resolve(v); }
    var timer = setTimeout(function () { mktUnguess(); fin(null); }, 3500);
    fetch(MKT + '/api/site/session', { mode: 'cors', credentials: 'include', cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        clearTimeout(timer);
        if (done) return;
        if (j && j.signed === true) { mktSignedIn(j); fin(MKT_ME); return; }
        if (j && j.signed === false) mktSetIn(false);   // ログインしていないと答えた時だけ印を消す（通信の失敗では消さない）
        mktUnguess();
        fin(null);
      })
      .catch(function () { clearTimeout(timer); mktUnguess(); fin(null); });
  });
  // ログアウト: マーケットの口へ POST（Content-Type を付けない＝単純な要求・preflight なし）。成功でも失敗でも印を消して読み直す（札が残っていれば、次の答えでまたログイン中の形）
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('[data-act="mkt-logout"]') : null;
    if (!b) return;
    e.preventDefault();
    b.disabled = true;
    mktSetIn(false);
    var back = function () { window.location.reload(); };
    try { fetch(MKT + '/api/auth/logout', { method: 'POST', mode: 'cors', credentials: 'include' }).then(back, back); } catch (err) { back(); }
  });

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

  // Report pages (/report, /report/<month>, /en/report...) and the research entry page (/research, /en/research): follow the page's own hreflang
  // alternates, so JP and EN land on the matching page (and the matching month) and never on a page that has no counterpart.
  if (loc === '/report' || loc.indexOf('/report/') === 0 || loc === '/research') {
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
  header.className = 'scix-header' + (isJa ? ' is-ja' : '');   // 日本語は名前が長いので、狭い幅（1101〜1279）で名前を枠の上の縁の見出しにする（CSS の .is-ja）
  header.id = 'scix-header';
  header.innerHTML = [
    '<div class="scix-header-overlay" id="scix-header-overlay"></div>',
    '<div class="scix-header-inner">',
    '  <a href="' + logoHref + '" class="scix-header-logo"><img src="/img/logo-navy.png" alt="ScienceX" width="91" height="36" decoding="async"></a>',
    '  <nav class="scix-header-nav" id="scix-header-nav" aria-label="' + navLabel + '">',
         nav[0],   // 蓄電所マーケットのまとまり（畳んだメニューでは一番上）
         authHtml('scix-auth-m'),   // 畳んだメニューだけ（広い帯では右端の .scix-auth）
         nav.slice(1).join('\n'),
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
      '.scix-nl button{flex:0 0 auto;font:inherit;font-size:.92rem;font-weight:700;padding:12px 24px;background:linear-gradient(135deg,#C2560A,#B45309);color:#fff;font-weight:900;border:none;border-radius:999px;cursor:pointer;white-space:nowrap;box-shadow:0 6px 16px rgba(234,88,12,.30)}',
      '.scix-nl button:hover{filter:brightness(.94)}',
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
      '<div class="scix-nl-label">メールのお知らせ</div>',
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
    var isReportPage = loc === '/report' || loc === '/report/flash' || /^\/report\/\d{4}-\d{2}$/.test(loc);   // 速報（/report/flash・2026-11-23）にも

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
          nlMount(rbox, loc === '/report' ? 'report_index' : (loc === '/report/flash' ? 'report_flash' : 'report_issue'), true);
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

  // 2026-11-23: 日本語の「買いたい」は引き出しの無い札になった。買う側の頁（GROUP_PAGES.buy）にいる間は、引き出しのあった時と同じに札を光らせる
  try {
    var topBuy = document.querySelector('.scix-header-nav a.scix-top-buy');
    if (topBuy && (GROUP_PAGES.buy || []).indexOf(loc) !== -1) topBuy.classList.add('active');
  } catch (err) { /* 光らなくても帯はそのまま */ }

  // --------------- 3b. Dropdown groups (買いたい / 売りたい / ナレッジ / 市場リサーチ) ---------------
  // 2026-11-23: 引き出しのある札は全部同じ動き。札（a）そのものが頁へのリンクで、
  //   ・マウス（hover のできる端末・広い帯）: 合わせると開く／押すと頁へ行く（押して開いたままにする形は作らない）。札と引き出しの間のすき間は CSS の橋でふさぎ、離れてから 140ms 待って閉じる＝下ろす途中で閉じない。
  //   ・指（touch・pen）と畳んだメニュー: 1回目の押下で開き（頁は移らない）、開いている札をもう一度押すと頁へ行く。
  //   ・キーボード: Enter は頁へ（click の detail が 0）・↓ で開いて最初のリンクへ・↑↓ で中を動く・Esc で閉じて札へ戻る。aria-expanded は開閉のたびに合わせる。
  //   別の札に合わせる・外を押す・Esc で閉じる。nav_open（open_by: hover／click／keyboard）はそのまま数える。
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
  var dds = header.querySelectorAll('.scix-nav-dd');

  function setOpen(dd, open, by) {
    dd.classList.toggle('open', open);
    dd.setAttribute('data-by', open ? (by || dd.getAttribute('data-by') || 'click') : '');
    var t = dd.querySelector('.scix-nav-dd-toggle');
    if (t) t.setAttribute('aria-expanded', open ? 'true' : 'false');
    var menu = dd.querySelector('.scix-nav-dd-menu');
    if (menu) {
      menu.style.left = '';
      if (open && !isNarrowNow()) {   // 右の端からはみ出す引き出しは、はみ出す分だけ左へ寄せる
        var r = menu.getBoundingClientRect();
        var over = r.right - (window.innerWidth - 12);
        if (over > 0) menu.style.left = (-over) + 'px';
      }
    }
  }
  function closeAllDropdowns(except) {
    for (var k = 0; k < dds.length; k++) {
      if (dds[k] !== except) setOpen(dds[k], false);
    }
  }
  // 札の押下が「引き出しを開くだけ」になるか（指・畳んだメニューで、まだ開いていない札の1回目）。キーボードの Enter・修飾キー付き・中ボタンは頁へ行く。
  // 計測（nav_click・market_click）も、開くだけの押下は数えない。
  function isTapMode(e) {
    return isNarrowNow() || !hoverCapable() || !!(e && (e.pointerType === 'touch' || e.pointerType === 'pen'));
  }
  function opensOnly(a, e) {
    if (!a || !a.classList || !a.classList.contains('scix-nav-dd-toggle')) return false;
    var dd = a.closest ? a.closest('.scix-nav-dd') : null;
    if (!dd || dd.classList.contains('open')) return false;
    if (e && (e.detail === 0 || e.button || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey)) return false;
    return isTapMode(e);
  }

  for (var d = 0; d < dds.length; d++) {
    (function (dd) {
      var key = dd.getAttribute('data-group');
      var toggle = dd.querySelector('.scix-nav-dd-toggle');   // 札（頁へのリンク）
      var menu = dd.querySelector('.scix-nav-dd-menu');
      var pages = GROUP_PAGES[key] || [];
      var holdsCurrent = pages.indexOf(loc) !== -1 || (key === 'knowledge' && isCol) ||
        (key === 'research' && (loc === '/report' || loc.indexOf('/report/') === 0));   // 市場ノートの号は「市場リサーチ」が光る（2026-11-22）
      if (holdsCurrent) {
        toggle.classList.add('active');
        dd.classList.add('is-current');
        // 畳んだメニューも、マーケットの帯と同じに全部閉じて始まる（今の頁の札は光るだけ・1回目で開き2回目で頁へ）
      }
      // 押下: 指・畳んだメニューの1回目は開くだけ。それ以外は頁へ（既定の動き）
      toggle.addEventListener('click', function (e) {
        if (!opensOnly(toggle, e)) return;
        e.preventDefault();
        closeAllDropdowns(dd);
        setOpen(dd, true, 'click');
        trackOpen(key, 'click');
      });
      // Keyboard: ↓ opens the group and moves focus to its first link; Enter keeps the native link (→ the page).
      toggle.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowDown') return;
        e.preventDefault();
        var wasOpen = dd.classList.contains('open');
        closeAllDropdowns(dd);
        setOpen(dd, true, 'key');
        if (!wasOpen) trackOpen(key, 'keyboard');
        var first = menu && menu.querySelector('a');
        if (first) first.focus();
      });
      // 引き出しの中: ↑↓ で行き来し、Esc で札へ戻る（Esc の閉じは下の keydown）
      if (menu) menu.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
        var items = menu.querySelectorAll('a');
        var at = Array.prototype.indexOf.call(items, document.activeElement);
        if (at === -1) return;
        e.preventDefault();
        var nx = e.key === 'ArrowDown' ? at + 1 : at - 1;
        if (nx < 0) { toggle.focus(); return; }
        if (nx < items.length) items[nx].focus();
      });
      // マウス: 合わせると開き、離れて 140ms 後に閉じる（途中でカーソルが札と引き出しの間を通っても閉じない）
      var hoverCounted = false, leaveTimer = 0;
      dd.addEventListener('pointerenter', function (e) {
        if (e.pointerType !== 'mouse' || isNarrowNow() || !hoverCapable()) return;
        clearTimeout(leaveTimer);
        closeAllDropdowns(dd);   // 一度に開くのは1つだけ（ほかの札に合わせたら、開いていた札は閉じる）
        if (!dd.classList.contains('open')) setOpen(dd, true, 'hover');
        if (hoverCounted) return;
        hoverCounted = true;
        trackOpen(key, 'hover');
      });
      dd.addEventListener('pointerleave', function (e) {
        if (e.pointerType !== 'mouse' || isNarrowNow()) return;
        clearTimeout(leaveTimer);
        leaveTimer = setTimeout(function () {
          if (dd.getAttribute('data-by') === 'hover') setOpen(dd, false);
        }, 140);
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
    links[j].addEventListener('click', function (e) { if (e.defaultPrevented) return; closeMenu(); closeAllDropdowns(null); });   // 札の1回目の押下（開くだけ・preventDefault 済み）では畳んだメニューを閉じない
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (isNarrowNow()) {
      // Drawer: close it, keep the accordion state (groups start folded; the current-page group only lights up).
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
    if (opensOnly(a, e)) return;   // 指・畳んだメニューの1回目（引き出しを開くだけ）は nav_open で数え、nav_click には数えない
    var group;
    if (a.classList.contains('scix-header-logo')) group = 'logo';
    else if (a.classList.contains('scix-mg-name')) group = 'market';   // まとまりの名前（蓄電所マーケットのトップへ・2026-11-23）
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
      else if (loc === '/report/flash') m = 'report-flash';
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
        if (e.type === 'click' && opensOnly(a, e)) return;   // 札の1回目の押下（引き出しを開くだけ）は、マーケットへの送客に数えない
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

  // --------------- 8. 下の帯（2026-11-23） ---------------
  // 中島「フッターがデザインがあってないどうだ？」（/column-aggregators-switching の画面の写しつき）。
  // 前の下の帯は濃い紺の一枚の帯・太字のリンクの羅列・上の帯と違う書体の文字のロゴで、今日作り替えた上の帯と合っていなかった。
  // 各頁の HTML にある <footer class="scix-footer"> を、DOM の準備ができたら組み替える（要素そのものは残し、class に scix-ft を足す・2回組まない）:
  //   1段目 ロゴ（上の帯と同じ画像・同じ行き先）／蓄電所マーケットのまとまり（印と名前・買いたい・売りたい・引き出しなし）／ログイン・無料で登録
  //   2段目 入口ごとの列（買いたい・売りたい・ナレッジ・市場リサーチ・会社）
  //   3段目 会社の行（頁の .scix-footer-company の言葉そのまま）と言葉の切り替え ／ 4段目 著作権の行（頁の .scix-footer-copyright そのまま）
  // 列の言葉は、上の帯の札・引き出しの言葉か、前の下の帯にある言葉だけ（O16-27）。前の下の帯にあった行き先で列に無い物は、その頁の言葉のまま近い列の末尾に足す（減らさない）。
  // /fund へのリンクは下の帯に1本だけ（O16-67）。マーケットへのリンクの出所の印（7a・placement=footer）と電話・メールの計測（5）は、要素が footer.scix-footer の中なので今のまま効く。
  // JavaScript が動かない時と組み替える前の一瞬は theme.css が同じ白い帯の形にする。
  try { (function () {
    function normHref(h) {
      try {
        var u = new URL(h, window.location.href);
        if (u.hostname === 'www.scix.co.jp' || u.hostname === 'scix.co.jp' || u.hostname === window.location.hostname) {
          var p = u.pathname.replace(/\.html$/, '').replace(/\/index$/, '').replace(/\/+$/, '');
          return p || '/';
        }
        return u.hostname + (u.pathname.replace(/\/+$/, '') || '/');
      } catch (err) { return h; }
    }
    var TAG = isZh ? EN_TAG : '';   // 中国語の画面でマーケット（英語の画面）と英語の市場ノートへ行く札には、上の帯と同じ「英文」の印
    // 列: k＝側（色）・h＝見出し・items＝[行き先, 言葉]
    // 行き先は下の帯の中で1回（O16-70・まとまりの名前と買いたいがマーケットのトップを指すのは例外）: 1段目にある行き先（ロゴ・まとまり・買いたい・売りたい・ログイン・登録）は列に重ねない。
    // 英語・中国語の「買う」の列は1段目と同じ1本しか無いので、中身は空（前の下の帯から足す物があれば出す・空なら列ごと出さない）。会社の列の Home・首页 はロゴと同じなので外した。
    var COLS = isZh ? [
      { k: 'buy', h: '购买', items: [['/zh-market-data', '市场数据']] },
      { k: 'knowledge', h: '洞见', items: [['/zh-knowledge', '洞见'], ['/zh-qa', '问答'], ['/zh-faq', '常见问题'], ['/zh-glossary', '术语表']] },
      { k: 'research', h: '市场研究', items: [['/en/report', '市场研究' + TAG]] },
      { k: 'co', h: '公司', items: [['/zh-company', '公司介绍'], ['/zh-contact', '联系我们'], ['@privacy', '隐私政策']] }
    ] : isEn ? [
      { k: 'buy', h: 'Buy', items: [['/en/market-data', 'Japan BESS Projects for Sale: Market Data']] },
      { k: 'knowledge', h: 'Knowledge', items: [['/en/knowledge', 'Knowledge'], ['/en/qa', 'Q&amp;A'], ['/en/glossary', 'Glossary'], ['/en/market-entry-guide', 'Market Entry Guide']] },
      // 2026-11-23: 市場リサーチは速報と月号の2本だけ（上の帯と同じ）。/en/market-data は行き先の title の言葉で「Buy」の列へ（O16-27）
      { k: 'research', h: 'Market Research', items: [['/en/report/flash', 'Market Notes: Daily Flash'], ['/en/report', 'Market Notes: Monthly Issue (on the 1st)']] },
      { k: 'co', h: 'Company', items: [['/en/company', 'Company'], ['/en/contact', 'Contact'], ['@privacy', 'Privacy Policy']] }
    ] : [
      // 2026-11-23（O16-72）: 列ごとに4つまで。上の帯から外した行き先の受け皿。売りたいの列の先頭は「蓄電所を出す（無料）」
      { k: 'buy', h: '買いたい', items: [['/transfer', '買うまでの流れ・買い方3つ'], ['/fund', 'ファンドで持つ'], ['/investors', '系統用蓄電池への投資'], ['/market-data', '系統用蓄電池の売り案件 市場データ']] },
      { k: 'sell', h: '売りたい', items: [[MKT + '/start/sell', '蓄電所を出す（無料）'], ['/sell-form', '当社に無料で売却査定'], ['/sourcing', '売るまでの流れ'], ['/partners', '案件・投資家を紹介する']] },
      { k: 'knowledge', h: 'ナレッジ', items: [['/knowledge', 'すべての記事（毎週更新）'], ['/qa', '入門Q&amp;A'], ['/grid-storage', '蓄電池事業のしくみ'], ['/column-somosomo', '蓄電池の、そもそも（連載20本）']] },
      { k: 'research', h: '市場リサーチ', items: [['/report/flash', '市場ノート 速報（毎日更新）'], ['/report', '市場ノート 月号（毎月1日）'], ['/report/data', '蓄電所の市場データ']] },
      { k: 'co', h: '会社', items: [['/company', '会社案内'], ['/contact', 'お問い合わせ'], ['@privacy', 'プライバシーポリシー']] }
    ];
    var PRIVACY_DEFAULT = isZh ? '/zh-privacy' : (isEn ? '/en/privacy' : '/privacy');
    // 前の下の帯にあって列に無い行き先を足す列（無ければ会社の列）
    function colFor(href) {
      var n = normHref(href);
      if (/needs$|\/(en\/)?(sourcing|sell-form|partners)$/.test(n)) return 'sell';
      if (/^dealroom\.scix\.co\.jp|\/(en\/)?(transfer|investors|fund|projects)$|^\/for\/|market-data$/.test(n)) return 'buy';
      if (/report|research/.test(n)) return 'research';
      if (/knowledge|qa$|faq$|glossary|grid-storage|primer|market-entry|guide-|column-/.test(n)) return 'knowledge';
      return 'co';
    }
    function flagSvg(code) {   // 上の帯の国旗と同じ絵。英国旗の clipPath の id は上の帯（scix-flag-uk）と重ならない名前にする
      return FLAG[code].replace('class="scix-flag"', 'class="scix-ft-flag"').replace(/scix-flag-uk/g, 'scix-ft-flag-uk');
    }
    function ftIc(k) { return ic(k).replace('class="scix-ic"', 'class="scix-ft-ic"'); }

    // 形の違う下の帯（/fund・/grid-storage・契約の流れの記事 日英＝class の無い <footer>）: 頁の言葉から、ほかの頁と同じ形の会社の行・著作権を作る。
    // 中身は頁の静的 HTML の言葉そのまま（社名・住所・TEL・MAIL・代表者・著作権・免責）。TEL・MAIL が文字だけの頁はリンクにする（ほかの頁と同じ）。
    function esc(t) { return t.replace(/[&<>]/g, function (m) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]; }); }
    function linkContact(line) {
      if (line.indexOf('<a') !== -1) return line;
      return line.replace(/(TEL:\s*)(\+?[0-9][0-9\- ]{6,}[0-9])/, function (m, a, num) { return a + '<a href="tel:' + num.replace(/[^0-9+]/g, '') + '">' + num + '</a>'; })
                 .replace(/(MAIL:\s*)([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})/, function (m, a, ad) { return a + '<a href="mailto:' + ad + '">' + ad + '</a>'; });
    }
    function adoptOther(ft) {
      if (!ft.querySelector('.scix-footer-nav')) return null;
      var name = '', lines = [], rep = '', copyHtml = '', parts = [];
      var info = ft.querySelector('.foot-info'), brand = ft.querySelector('.foot-brand');
      if (info) {
        if (brand) { var bc = brand.cloneNode(true); var rm = bc.querySelectorAll('b, div'); for (var r = 0; r < rm.length; r++) rm[r].parentNode.removeChild(rm[r]); name = esc(bc.textContent.replace(/^\s+|\s+$/g, '')); }
        parts = info.innerHTML.split(/<br\s*\/?>/i);
      } else {
        var kids = [];
        for (var k = 0; k < ft.children.length; k++) {
          var ch = ft.children[k];
          if (ch.tagName !== 'DIV' || ch.classList.contains('scix-footer-nav') || /©/.test(ch.textContent)) continue;
          kids.push(ch);
        }
        if (kids.length < 2) return null;
        name = esc(kids[0].textContent.replace(/^\s+|\s+$/g, ''));
        parts = kids[1].innerHTML.split(/<br\s*\/?>/i);
        if (kids[2]) parts.push(kids[2].innerHTML);
      }
      for (var i = 0; i < parts.length; i++) {
        var ln = parts[i].replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, '');
        if (!ln) continue;
        if (/代表取締役|Representative Director/.test(ln)) { rep = ln; continue; }
        // 「TEL: …　MAIL: …」「TEL: …｜MAIL: …」は2つの区切りに分ける
        var two = ln.split(/\s*[｜|　]\s*(?=MAIL)|\s+(?=MAIL:)/);
        for (var t = 0; t < two.length; t++) lines.push(linkContact(two[t].replace(/[　\s]+$/, '')));
      }
      var cp = ft.querySelector('.copy');
      if (!cp) { for (var c2 = ft.children.length - 1; c2 >= 0; c2--) if (/©/.test(ft.children[c2].textContent)) { cp = ft.children[c2]; break; } }
      if (cp) copyHtml = cp.innerHTML;
      if (!name || !lines.length || !copyHtml) return null;
      var company = document.createElement('div');
      company.innerHTML = '<div class="company-name">' + name + '</div>' + lines.join('<br>') + (rep ? '<div class="representative">' + rep + '</div>' : '');
      var copy = document.createElement('div');
      copy.innerHTML = copyHtml;
      // 免責の段は下の帯の上へ移す（言葉はそのまま）
      var disc = ft.querySelector('.disc'), discHtml = '';
      if (disc) {
        var hh = disc.querySelector('h5, h4, h3');
        if (hh) discHtml += '<p class="scix-ft-disc-h">' + hh.innerHTML + '</p>';
        var ps = disc.querySelectorAll('p');
        for (var q = 0; q < ps.length; q++) discHtml += '<p>' + ps[q].innerHTML + '</p>';
      }
      return { company: company, copy: copy, disc: discHtml };
    }

    function build(ft) {
      if (!ft || ft.classList.contains('scix-ft')) return;
      var company = ft.querySelector('.scix-footer-company');
      var copy = ft.querySelector('.scix-footer-copyright');
      var discHtml = '';
      if ((!company || !copy) && !ft.classList.contains('scix-footer')) {
        var ad = adoptOther(ft);
        if (ad) { company = ad.company; copy = ad.copy; discHtml = ad.disc; }
      }
      if (!company || !copy) return;   // 読めない形の下の帯は組み替えない＝theme.css の白い帯のまま
      // 前の下の帯のリンク（行き先と言葉）
      var olds = [];
      var oldLinks = ft.querySelectorAll('.scix-footer-nav a[href]');
      for (var i = 0; i < oldLinks.length; i++) olds.push([oldLinks[i].getAttribute('href'), oldLinks[i].innerHTML.replace(/^\s+|\s+$/g, '')]);
      var privacy = PRIVACY_DEFAULT;
      for (var p = 0; p < olds.length; p++) if (/privacy$/.test(normHref(olds[p][0]))) { privacy = olds[p][0]; break; }

      // 列を組む（無い列は出さない）。1段目にある行き先は列に重ねない
      var cols = [], have = {};
      var TOP = [logoHref, MG.href, isJa ? MKT + '/' : MKT + '/en', isJa ? MKT + '/needs' : MKT + '/en/needs', AUTH.login, AUTH.reg];
      for (var tp = 0; tp < TOP.length; tp++) have[normHref(TOP[tp])] = 1;
      for (var c = 0; c < COLS.length; c++) {
        var col = { k: COLS[c].k, h: COLS[c].h, items: [] };
        for (var j = 0; j < COLS[c].items.length; j++) {
          var href = COLS[c].items[j][0] === '@privacy' ? privacy : COLS[c].items[j][0];
          col.items.push([href, COLS[c].items[j][1]]);
          have[normHref(href)] = 1;
        }
        cols.push(col);
      }
      for (var o = 0; o < olds.length; o++) {
        var nh = normHref(olds[o][0]);
        if (have[nh]) continue;
        var want = colFor(olds[o][0]), put = null;
        for (var q = 0; q < cols.length; q++) if (cols[q].k === want) put = cols[q];
        if (!put) put = cols[cols.length - 1];
        have[nh] = 1;
        if (put.items.length >= 4) continue;   // 2026-11-23（O16-72）: 列ごとに4つまで。前の下の帯の行き先でも、列が埋まっていれば足さない
        put.items.push([olds[o][0], olds[o][1]]);
      }

      // 会社の行: 頁の言葉そのまま（社名・<br> で区切られた行・代表者）。住所の続きの行は1つにまとめ、TEL・MAIL は別の区切りにする
      var segs = [], name = '', rep = '', cur = null;
      var nameEl = company.querySelector('.company-name'), repEl = company.querySelector('.representative');
      if (nameEl) name = nameEl.innerHTML.replace(/^\s+|\s+$/g, '');
      if (repEl) rep = repEl.innerHTML.replace(/^\s+|\s+$/g, '');
      var kids = company.childNodes;
      for (var kq = 0; kq < kids.length; kq++) {
        var nd = kids[kq];
        if (nd === nameEl || nd === repEl) continue;
        if (nd.nodeType === 1 && nd.tagName === 'BR') { cur = null; continue; }
        var htm = nd.nodeType === 3 ? nd.nodeValue.replace(/[&<>]/g, function (m) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]; }) : (nd.nodeType === 1 ? nd.outerHTML : '');
        if (!htm.replace(/\s+/g, '')) { if (cur) cur.h += ' '; continue; }
        var isContact = /^\s*(TEL|MAIL)\b/.test(nd.nodeType === 3 ? nd.nodeValue : '');
        if (!cur) {
          var prevSeg = segs[segs.length - 1];
          if (!isContact && prevSeg && prevSeg.addr) { cur = prevSeg; cur.h += ' '; }
          else { cur = { h: '', addr: !isContact }; segs.push(cur); }
        }
        cur.h += htm;
      }
      var info = (name ? '<span class="scix-ft-seg scix-ft-name">' + name + '</span>' : '');
      for (var sg = 0; sg < segs.length; sg++) {
        var t = segs[sg].h.replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, '');
        if (t) info += '<span class="scix-ft-seg' + (segs[sg].addr ? ' is-addr' : '') + '">' + t + '</span>';
      }
      if (rep) info += '<span class="scix-ft-seg">' + rep + '</span>';

      // 1段目
      var mg = '<div class="scix-ft-mg" role="group" aria-label="' + MG.name + '">' +
        '<a class="scix-ft-mg-name" href="' + MG.href + '" title="' + MG.title + '">' + MG_MARK.replace('class="scix-mg-mark"', 'class="scix-ft-mark"') + '<span>' + MG.name + '</span></a>' +
        (isJa
          ? '<a class="scix-ft-side is-buy" href="' + MKT + '/">' + ftIc('buy') + '<span>買いたい</span></a>' +
            '<a class="scix-ft-side is-sell" href="' + MKT + '/needs">' + ftIc('sell') + '<span>売りたい</span></a>'
          : '<a class="scix-ft-side is-buy" href="' + MKT + '/en">' + ftIc('buy') + '<span>' + (isZh ? '购买' : 'Buy') + '</span></a>' +
            '<a class="scix-ft-side is-sell" href="' + MKT + '/en/needs">' + ftIc('sell') + '<span>' + (isZh ? '出售' : 'Sell') + '</span></a>') +
        '</div>';
      var auth = '<div class="scix-ft-auth">' +
        '<a href="' + AUTH.login + '" class="scix-ft-login">' + AUTH_ICON + '<span>' + AUTH.lt + '</span></a>' +
        '<a href="' + AUTH.reg + '" class="scix-ft-reg">' + AUTH.rt + '</a></div>';

      // 2段目
      var colsHtml = '', ncol = 0;
      function plain(h) { return h.replace(/<span class="scix-en-tag">[^<]*<\/span>/g, '').replace(/<[^>]*>/g, '').replace(/^\s+|\s+$/g, ''); }
      for (var cc = 0; cc < cols.length; cc++) {
        var its = cols[cc].items.slice();
        if (!its.length) continue;
        var hid = 'scix-ft-h-' + cols[cc].k, head = cols[cc].h;
        // 1本目が見出しと同じ言葉なら、見出しそのものをその頁へのリンクにして1本目を外す（同じ言葉を2つ並べない）
        if (plain(its[0][1]) === plain(head)) { head = '<a href="' + its[0][0] + '">' + its[0][1] + '</a>'; its.shift(); }
        ncol++;
        colsHtml += '<div class="scix-ft-col is-' + cols[cc].k + '"><h2 class="scix-ft-h" id="' + hid + '">' + head + '</h2>';
        if (its.length) {
          colsHtml += '<ul aria-labelledby="' + hid + '">';
          for (var ci = 0; ci < its.length; ci++) colsHtml += '<li><a href="' + its[ci][0] + '">' + its[ci][1] + '</a></li>';
          colsHtml += '</ul>';
        }
        colsHtml += '</div>';
      }

      // 3段目の言葉の切り替え（行き先は上の帯と同じ）
      function ftLang(code, href, label, on) {
        return '<a href="' + href + '" hreflang="' + code + '" lang="' + code + '" aria-label="' + label + '"' +
          (on ? ' class="active" aria-current="true"' : '') + '>' + flagSvg(code) + '</a>';
      }
      var lang = '<div class="scix-ft-lang" role="group" aria-label="' + (isEn ? 'Language' : (isZh ? '语言' : '言語')) + '">' +
        ftLang('ja', jpHref, '日本語', isJa) + ftLang('en', enHref, 'English', isEn) + ftLang('zh', zhHref, '中文', isZh) + '</div>';

      var copyHtml = copy.innerHTML.replace(/^\s+|\s+$/g, '');
      if (!ft.classList.contains('scix-footer')) {   // 形の違う下の帯: ほかの頁と同じ帯にする（頁の style 属性の紺の地・中央寄せは外す）
        ft.removeAttribute('style');
        ft.classList.add('scix-footer');
        if (discHtml && ft.parentNode) {
          var dz = document.createElement('aside');
          dz.className = 'scix-ft-disc';
          dz.setAttribute('aria-label', isEn ? 'Disclaimer' : '免責事項');
          dz.innerHTML = '<div class="scix-ft-disc-in">' + discHtml + '</div>';
          ft.parentNode.insertBefore(dz, ft);
        }
      }
      ft.classList.add('scix-ft');
      ft.innerHTML = '<div class="scix-ft-in">' +
        '<div class="scix-ft-top">' +
          '<a href="' + logoHref + '" class="scix-ft-logo"><img src="/img/logo-navy.png" alt="ScienceX" width="97" height="38" loading="lazy" decoding="async"></a>' +
          mg + auth +
        '</div>' +
        '<nav class="scix-ft-cols n' + Math.min(Math.max(ncol, 2), 5) + '" aria-label="' + (isEn ? 'Site map' : (isZh ? '网站导航' : 'サイトの案内')) + '">' + colsHtml + '</nav>' +
        '<div class="scix-ft-co"><p class="scix-ft-info"><span class="scix-ft-info-in">' + info + '</span></p>' + lang + '</div>' +
        '<p class="scix-ft-copy">' + copyHtml + '</p>' +
      '</div>';
      mktPaint(ft);   // ログイン中と分かっていれば、下の帯の「ログイン」「無料で登録」もログイン中の形に（2026-11-23）
    }
    function buildAll() {
      try {
        var fts = document.querySelectorAll('footer.scix-footer, body > footer');
        for (var f = 0; f < fts.length; f++) build(fts[f]);
      } catch (err) { /* 組み替えられなくても theme.css の白い帯のまま */ }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', buildAll);
    else buildAll();
  })(); } catch (err) { /* 下の帯を組み替えられなくても頁はそのまま */ }

  // --------------- 5b. 本文の表が画面より広い時は、表の中だけ横に動かす（2026-11-23） ---------------
  // スマホ幅で列の多い表が頁を横に広げ、上の帯ごとずれていた。収まる表は今のまま（印を付けない）、はみ出す表だけ
  // table.scix-tscroll（theme.css＝表を箱にして横に送る）にする。幅が変わったら測り直す。
  try { (function () {
    function mark() {
      var ts = document.querySelectorAll('body table');
      for (var i = 0; i < ts.length; i++) ts[i].classList.remove('scix-tscroll');
      for (var j = 0; j < ts.length; j++) {
        var t = ts[j], box = t.parentElement;
        if (!box || t.closest('.rp-table, .md-scroll, .c47scroll, .c50scroll, .scix-header, footer')) continue;
        var bs = getComputedStyle(box), ox = bs.overflowX;
        if (ox === 'auto' || ox === 'scroll') continue;   // 頁が自分で横に送る箱に入れている表はそのまま
        if (t.getBoundingClientRect().right > box.getBoundingClientRect().right - parseFloat(bs.paddingRight || 0) - parseFloat(bs.borderRightWidth || 0) + 1) t.classList.add('scix-tscroll');
      }
    }
    var timer = 0, lastW = window.innerWidth;
    function onResize() { if (window.innerWidth === lastW) return; lastW = window.innerWidth; clearTimeout(timer); timer = setTimeout(mark, 150); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mark); else mark();
    window.addEventListener('load', mark);
    window.addEventListener('resize', onResize);
  })(); } catch (err) { /* 測れなくても表はそのまま */ }

  // --------------- 6. 面談の予約について ---------------
  // 2026-09-05 撤去。Googleカレンダーの「予約スケジュール」は Google Meet のリンクを発行するため、
  // 「こちらが主催する会議は必ず Zoom」（2026-08-23 決定）に反する。
  // 面談は問い合わせへの返信で候補日時を出して決める。各ページの予約ボタンも同時に削除した。
  // 復活させるときは Zoom 側の予約ページを用意してからにする。

})();
