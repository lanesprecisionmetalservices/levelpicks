#!/usr/bin/env python3
"""Builds the Level Picks static site from site.json into ./docs.

Add a product:  append an object to a guide's "products" list in site.json.
                Needs name, badge, url (or search), summary, specs, good_for, watch_for.
                Optional: asin, icon, featured (1 = first on the homepage), hands_on (true once
                you've filmed it), video (YouTube or TikTok link), image (your own photo, put
                the file in ./media and write "media/<file>").
Add a guide:    append an object to "guides" and add its slug to a category in "categories".
Add a book:     append to "books" (status "coming_soon" or "available" with a "url").
Then run:       python3 build.py

Pages:
  /                 home
  /picks/           every product, filter by category, search
  /p/<slug>/        one product
  /guides/          every guide, grouped by category
  /guides/<slug>/   one guide
  /books/           buying-guide books
  /about/ /disclosure/ /privacy/ /404.html
"""
import json, html, os, re, shutil, urllib.parse
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
S = json.load(open(os.path.join(ROOT, "site.json")))
e = html.escape

DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."
DISCLOSURE_LONG = ("As an Amazon Associate I earn from qualifying purchases. Links to Amazon on this site "
                   "are affiliate links. If you buy through one, the site may earn a commission. "
                   "The price you pay is the same.")

GTAG = '''<script async src="https://www.googletagmanager.com/gtm.js?id=GTM-KV9KN5R7"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
</script>'''

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800'
         '&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">')

# ───────────────────────── data helpers ─────────────────────────
GUIDES = {g["slug"]: g for g in S["guides"]}
CATS = S.get("categories", [])
CAT_OF = {}
for c in CATS:
    for gs in c["guides"]:
        CAT_OF[gs] = c
FALLBACK_CAT = {"slug": "more", "name": "More picks", "color": "#ffc531", "icon": "box", "blurb": "", "guides": []}
for g in S["guides"]:
    CAT_OF.setdefault(g["slug"], FALLBACK_CAT)


def slugify(s, n=60):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    if len(s) > n:
        s = s[:n].rsplit("-", 1)[0]
    return s


PRODUCTS = []  # every product once, with its guide and category
_seen = set()
for g in S["guides"]:
    for p in g["products"]:
        base = slugify(p["name"])
        slug, k = base, 2
        while slug in _seen:
            slug, k = f"{base}-{k}", k + 1
        _seen.add(slug)
        p["_slug"], p["_guide"], p["_cat"] = slug, g, CAT_OF[g["slug"]]
        PRODUCTS.append(p)
N_PRODUCTS, N_GUIDES = len(PRODUCTS), len(S["guides"])


def amazon_link(query):
    q = {"k": query}
    if S["amazon_tag"]:
        q["tag"] = S["amazon_tag"]
    return "https://www.amazon.com/s?" + urllib.parse.urlencode(q)


def product_link(p):
    return p.get("url") or amazon_link(p["search"])


def cta_text(p, short=False):
    if p.get("cta") and not short:
        return p["cta"]
    if not p.get("url"):
        return "See options" if short else "See options on Amazon"
    return "Check price" if short else "Check price on Amazon"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def styled_title(t):
    """'Main part: the rest' -> main part, then the rest in the italic serif accent."""
    if ":" in t:
        a, b = t.split(":", 1)
        return f'{e(a.strip())}<em>{e(b.strip())}</em>'
    return e(t)


def plain_title(t):
    return t.split(":", 1)[0].strip()


def youtube_id(u):
    m = re.search(r"(?:youtu\.be/|v=|/shorts/|/embed/)([A-Za-z0-9_-]{11})", u or "")
    return m.group(1) if m else None


# ───────────────────────── icons ─────────────────────────
ICONS = {
    "helmet": '<path d="M4 13a8 8 0 0 1 16 0v3a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3z"/><rect x="7" y="11" width="10" height="4" rx="1"/><path d="M12 5V3"/>',
    "goggles": '<path d="M2 10c0-1.7 1.3-3 3-3h14c1.7 0 3 1.3 3 3v3c0 1.7-1.3 3-3 3h-3l-2-2.5h-4L8 16H5c-1.7 0-3-1.3-3-3z"/><path d="M5 10.5h4.5M14.5 10.5H19"/>',
    "grinder": '<circle cx="7" cy="12" r="4.5"/><circle cx="7" cy="12" r="1"/><path d="M11.5 10.5h7a2.5 2.5 0 0 1 0 5h-7"/><path d="M15 10.5V8"/>',
    "plasma": '<path d="M3 20l7-7"/><rect x="9" y="7.5" width="8" height="4" rx="1.5" transform="rotate(-45 13 9.5)"/><path d="M16 5l3-2M18 8l3-.5M16.5 2.5l.5-1.5"/>',
    "drill": '<path d="M3 8h11l2 2v1H3z"/><path d="M16 9.5h5"/><path d="M6 11l-1 8h4l1-8"/><path d="M9 15h3"/>',
    "saw": '<circle cx="12" cy="13" r="6"/><circle cx="12" cy="13" r="1.4"/><path d="M12 7V4M18 13h3M3 20h18"/>',
    "gauge": '<path d="M4 16a8 8 0 1 1 16 0"/><path d="M12 16l4-5"/><path d="M4 20h16"/>',
    "battery": '<rect x="4" y="6" width="16" height="14" rx="2"/><path d="M9 3h6v3H9z"/><path d="M13 9l-3 4h4l-3 4"/>',
    "earbuds": '<path d="M7 4a3 3 0 0 0-3 3v2a3 3 0 0 0 3 3h1V4z"/><path d="M8 12v8"/><path d="M17 4a3 3 0 0 1 3 3v2a3 3 0 0 1-3 3h-1V4z"/><path d="M16 12v8"/>',
    "monitor": '<path d="M2 6c6-2 14-2 20 0v9c-6 2-14 2-20 0z"/><path d="M12 17v3M8 20h8"/>',
    "tv": '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M8 20h8M12 16v4"/>',
    "mouse": '<rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 3v6"/>',
    "headphones": '<path d="M4 15v-3a8 8 0 0 1 16 0v3"/><rect x="3" y="14" width="4" height="6" rx="1.5"/><rect x="17" y="14" width="4" height="6" rx="1.5"/>',
    "mixer": '<path d="M5 4h10a3 3 0 0 1 3 3v2H8"/><path d="M8 9v4"/><path d="M5 13h9l-1.5 7h-6z"/><path d="M15 9v11"/>',
    "rotary": '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M11 15h2v3h-2z"/><path d="M12 18v3"/>',
    "gift": '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v8h14v-8M12 8v12"/><path d="M12 8c-2-4-6-4-6-1s6 1 6 1 6 2 6-1-4-3-6 1"/>',
    "gamepad": '<path d="M6 8h12a4 4 0 0 1 3.8 5.2l-1 3.2a2.5 2.5 0 0 1-4.3.8L15 15H9l-1.5 2.2a2.5 2.5 0 0 1-4.3-.8l-1-3.2A4 4 0 0 1 6 8z"/><path d="M7 11v3M5.5 12.5h3"/><circle cx="16" cy="11.5" r=".6"/><circle cx="17.5" cy="13" r=".6"/>',
    "bolt": '<path d="M13 2L5 13h6l-1 9 8-11h-6z"/>',
    "scanner": '<rect x="5" y="3" width="14" height="18" rx="2"/><rect x="8" y="6" width="8" height="6" rx="1"/><path d="M8 16h2M14 16h2"/>',
    "magnet": '<path d="M5 3h4v8a3 3 0 0 0 6 0V3h4v8a7 7 0 0 1-14 0z"/><path d="M5 7h4M15 7h4"/>',
    "light": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    "thermo": '<path d="M10 4a2 2 0 0 1 4 0v10a4 4 0 1 1-4 0z"/><path d="M12 9v7"/>',
    "pan": '<circle cx="9" cy="13" r="6"/><path d="M15 13h7"/>',
    "book": '<path d="M4 5a2 2 0 0 1 2-2h13v15H6a2 2 0 0 0-2 2z"/><path d="M4 20a2 2 0 0 0 2 2h13v-4"/><path d="M8 7h7"/>',
    "car": '<path d="M5 11l2-5h10l2 5"/><rect x="3" y="11" width="18" height="6" rx="2"/><circle cx="7.5" cy="17.5" r="1.5"/><circle cx="16.5" cy="17.5" r="1.5"/>',
    "tag": '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.5"/>',
    "box": '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "out": '<path d="M7 17L17 7M9 7h8v8"/>',
    "play": '<path d="M8 5v14l11-7z"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "tiktok": '<path d="M14 3v11.5a3.5 3.5 0 1 1-3-3.46"/><path d="M14 3c.5 2.5 2.3 4 5 4"/>',
    "youtube": '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10 9v6l5-3z"/>',
    "instagram": '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.3" cy="6.7" r=".6"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "spec": '<path d="M4 6h16M4 12h10M4 18h13"/>',
    "film": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 5v14M17 5v14M3 9h4M3 15h4M17 9h4M17 15h4"/>',
}


def icon(name, cls="i"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(name, ICONS["box"])}</svg>')


def art(p, up, size=""):
    """Product art: the owner's photo if one is set, else a colored icon tile."""
    c = p["_cat"]["color"]
    stamp = ('<span class="stamp">' + icon("film") + 'Filmed hands-on</span>') if p.get("hands_on") else ""
    if p.get("image"):
        inner = f'<img src="{up}{e(p["image"])}" alt="{e(p["name"])}" loading="lazy">'
    else:
        inner = f'<span class="art-ring"></span>{icon(p.get("icon", "box"), "art-i")}'
    return f'<div class="art {size}" style="--c:{c}">{inner}{stamp}</div>'


def buy_btn(p, cls="btn", short=False, where=""):
    return (f'<a class="{cls}" href="{e(product_link(p))}" target="_blank" rel="sponsored nofollow noopener" '
            f'data-buy="{e(p["name"])}" data-where="{where}">{e(cta_text(p, short))}{icon("out", "i sm")}</a>')


def card(p, up, where="card"):
    c, g = p["_cat"], p["_guide"]
    href = f'{up}p/{p["_slug"]}/'
    text = " ".join([p["name"], g.get("short", ""), c["name"], p["summary"]]).lower()
    return f"""
<article class="card rv" data-cat="{c['slug']}" data-text="{e(text)}" style="--c:{c['color']}">
  <a class="card-art" href="{href}" tabindex="-1" aria-hidden="true">{art(p, up)}</a>
  <div class="card-body">
    <span class="k">{e(c['name'])} · {e(g.get('short') or plain_title(g['title']))}</span>
    <h3><a href="{href}">{e(p['name'])}</a></h3>
    <p class="card-badge">{e(p['badge'])}</p>
    <p class="card-sum">{e(p['summary'])}</p>
    <div class="card-cta">{buy_btn(p, "btn sm", True, where)}<a class="lnk" href="{href}">Details{icon('arrow', 'i sm')}</a></div>
  </div>
</article>"""


# ───────────────────────── page shell ─────────────────────────
def promo_bar(up):
    pr = S.get("promo")
    if not pr or pr.get("guide") not in GUIDES:
        return ""
    return f"""<a class="promo" href="{up}guides/{pr['guide']}/" data-ends="{e(pr['ends'])}" hidden>
  <span class="dot"></span><b>{e(pr['label'])}</b><span class="sep">·</span><span data-count>{e(pr['ends_text'])}</span>
  <span class="promo-go">See the deals{icon('arrow', 'i sm')}</span></a>"""


def nav_links(up, active):
    pr = S.get("promo")
    items = [("picks", "All picks", f"{up}picks/"), ("guides", "Guides", f"{up}guides/")]
    if pr and pr.get("guide") in GUIDES:
        items.append(("deals", "Deals", f"{up}guides/{pr['guide']}/"))
    items += [("books", "Books", f"{up}books/"), ("about", "About", f"{up}about/")]
    return "".join(f'<a href="{h}"{" aria-current=page" if k == active else ""}{" data-deal" if k == "deals" else ""}>{t}</a>'
                   for k, t, h in items)


def socials(cls="soc"):
    out = []
    for k, label in (("tiktok", "TikTok"), ("youtube", "YouTube"), ("instagram", "Instagram")):
        u = S.get("social", {}).get(k)
        if u:
            out.append(f'<a class="{cls}" href="{e(u)}" target="_blank" rel="noopener">{icon(k)}<span>{label}</span></a>')
    return "".join(out)


def footer(up):
    cols = []
    for c in CATS:
        links = "".join(f'<a href="{up}guides/{gs}/">{e(GUIDES[gs].get("short") or plain_title(GUIDES[gs]["title"]))}</a>'
                        for gs in c["guides"] if gs in GUIDES)
        cols.append(f'<div><h4 style="--c:{c["color"]}">{e(c["name"])}</h4>{links}</div>')
    return f"""
<footer class="foot">
  <div class="foot-cta">
    <div><span class="k">Not finding it?</span><h2>Every pick, <em>one page.</em></h2></div>
    <div class="foot-cta-btns"><a class="btn" href="{up}picks/">Browse all {N_PRODUCTS} picks{icon('arrow', 'i sm')}</a><a class="btn ghost" href="{up}guides/">See every guide</a></div>
  </div>
  <div class="foot-in">
    <div class="foot-brand">
      <a class="brand" href="{up}"><span class="vial"><i></i></span>{e(S["name"])}</a>
      <p class="tag">Honest picks. <em>Perfectly level.</em></p>
      <div class="socs">{socials()}</div>
    </div>
    <div class="foot-cols">{''.join(cols)}
      <div><h4>Level Picks</h4><a href="{up}picks/">All picks</a><a href="{up}guides/">All guides</a><a href="{up}books/">Buying-guide books</a><a href="{up}about/">About &amp; how I pick</a><a href="{up}disclosure/">Affiliate disclosure</a><a href="{up}privacy/">Privacy</a></div>
    </div>
  </div>
  <p class="fine">{e(DISCLOSURE_LONG)} Product details come from manufacturer and retailer specs. Prices change, so check the current listing before you buy. Updated {e(S["updated"])}.</p>
</footer>"""


def page(title, desc, body, depth, active=None, canonical="", jsonld=None, after=""):
    up = "../" * depth
    ld = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>' if jsonld else ""
    og_img = f'{S["base_url"]}/brand/levelpicks_profile_1080.png'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{GTAG}
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#070b16">
<link rel="canonical" href="{e(S['base_url'])}/{canonical}">
<link rel="icon" href="{up}brand/levelpicks_icon_1080.png">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(S['base_url'])}/{canonical}">
<meta property="og:image" content="{og_img}">
<meta name="twitter:card" content="summary">
{FONTS}
<link rel="stylesheet" href="{up}style.css">
<script>document.documentElement.classList.add("js")</script>
{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="glow" aria-hidden="true"></div>
<header class="top">
  {promo_bar(up)}
  <div class="bar">
    <a class="brand" href="{up}" aria-label="{e(S['name'])} home"><span class="vial"><i></i></span>{e(S["name"])}</a>
    <nav class="links" aria-label="Main">{nav_links(up, active)}</nav>
    <div class="bar-r">
      <a class="search-btn" href="{up}picks/#search" aria-label="Search picks">{icon('search')}<span>Search</span></a>
      <details class="menu"><summary aria-label="Menu">{icon('menu', 'i open')}{icon('x', 'i shut')}</summary>
        <div class="sheet"><nav aria-label="Menu">{nav_links(up, active)}</nav>
          <div class="sheet-cats">{''.join(f'<a href="{up}picks/#{c["slug"]}" style="--c:{c["color"]}">{icon(c["icon"])}{e(c["name"])}</a>' for c in CATS)}</div>
          <div class="socs">{socials()}</div></div>
      </details>
    </div>
  </div>
  <div class="progress" aria-hidden="true"><b></b></div>
</header>
<main id="main">
{body}
</main>
{footer(up)}
{after}
<script>{JS}</script>
</body>
</html>
"""


def write(rel, content):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(content)


def crumbs(items):
    """items: list of (label, href or None)."""
    parts = []
    for label, href in items:
        parts.append(f'<a href="{href}">{e(label)}</a>' if href else f'<span aria-current="page">{e(label)}</span>')
    return f'<nav class="crumbs" aria-label="Breadcrumb">{"<i>/</i>".join(parts)}</nav>'


def crumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": f'{S["base_url"]}/{u}'} for i, (n, u) in enumerate(items, 1)]}


# ───────────────────────── shared sections ─────────────────────────
def how_i_pick(up, compact=False):
    steps = [
        ("Specs from the maker", "Every number comes from the manufacturer's or retailer's own listing. If it can't be checked, it isn't on the page."),
        ("The catch, out loud", "Each pick says who it isn't for, what it can't do, and what renews if you forget to cancel."),
        ("Nobody pays to be here", "No brand buys a spot on a list. Amazon pays a small commission on purchases, and your price doesn't change."),
    ]
    items = "".join(f'<div class="how-i"><h3>{t}</h3><p>{d}</p></div>' for t, d in steps)
    more = "" if compact else f'<a class="lnk" href="{up}about/">More about how picks get made{icon("arrow", "i sm")}</a>'
    return f"""
<section class="sect how rv">
  <h2 class="h2">How picks get made</h2>
  <div class="how-row">{items}</div>
  {more}
</section>"""


def follow_block(up):
    if not socials():
        return ""
    return f"""
<section class="sect band follow rv" style="--c:#ff6b8b">
  <h2 class="h2 big">See it before <em>you buy it.</em></h2>
  <p class="band-p">Short hands-on videos of the picks: how they work, how they hold up, and what bugs me about them. New ones go up all through Black Friday week.</p>
  <div class="socs">{socials()}</div>
</section>"""


def books_teaser(up):
    b = next(iter(S.get("books", [])), None)
    if not b:
        return ""
    soon = b.get("status") != "available"
    btn_text = "See what's inside" if soon else "Get the book"
    return f"""
<section class="sect books-teaser rv">
  <div class="bt-cover" aria-hidden="true"><span class="bt-k">Level Picks</span><strong>{e(b['title'])}</strong><span class="bt-v"><span class="vial"><i></i></span></span></div>
  <div>
    <p class="note">{'Coming soon' if soon else 'Out now'}</p>
    <h2 class="h2">The whole build, start to finish.</h2>
    <p class="band-p">The site gives you the short list. The books go all the way: the best, the budget and the bare minimum, how it goes together, and what to skip. First up is <b>{e(b['title'])}</b>.</p>
    <a class="lnk big" href="{up}books/">{btn_text}{icon('arrow', 'i sm')}</a>
  </div>
</section>"""


def related(p, n=4):
    same = [q for q in p["_guide"]["products"] if q is not p]
    cat = [q for q in PRODUCTS if q["_cat"] is p["_cat"] and q is not p and q not in same]
    rest = sorted([q for q in PRODUCTS if q is not p and q not in same and q not in cat],
                  key=lambda q: q.get("featured", 99))
    return (same + cat + rest)[:n]


# ───────────────────────── pages ─────────────────────────
def home():
    up = ""
    feats = sorted([p for p in PRODUCTS if p.get("featured")], key=lambda p: p["featured"])[:8]
    cats = "".join(
        f'<a href="picks/#{c["slug"]}" style="--c:{c["color"]}">{icon(c["icon"], "i cf")}<span>{e(c["name"])}</span>'
        f'<sup>{sum(len(GUIDES[g]["products"]) for g in c["guides"] if g in GUIDES)}</sup></a>'
        for c in CATS)
    spot = GUIDES.get(S.get("spotlight", "plasma-cutters"))
    spot_html = ""
    if spot:
        sp = spot["products"][0]
        sc = CAT_OF[spot["slug"]]
        spot_html = f"""
<section class="sect band spot rv" style="--c:{sc['color']}">
  <div class="spot-art">{art(sp, up, 'xl')}</div>
  <div class="spot-body">
    <p class="note">New guide</p>
    <h2>{styled_title(spot['title'])}</h2>
    <p>{e(spot['intro'])}</p>
    <div class="cta-row"><a class="btn" href="guides/{spot['slug']}/">Read the guide{icon('arrow', 'i sm')}</a>{buy_btn(sp, 'lnk', True, 'home-spotlight')}</div>
  </div>
</section>"""
    guide_list = "".join(
        f'<a class="gl" href="guides/{g["slug"]}/" style="--c:{CAT_OF[g["slug"]]["color"]}"><b>{e(plain_title(g["title"]))}</b>'
        f'<small>{plural(len(g["products"]), "pick")}</small>{icon("arrow", "i sm")}</a>'
        for g in S["guides"])
    pr = S.get("promo") or {}
    deal_href = f'guides/{pr["guide"]}/' if pr.get("guide") in GUIDES else "picks/"
    body = f"""
<section class="home-hero">
  <div class="hh-copy">
    <h1>Honest picks.<em>Perfectly level.</em></h1>
    <p class="lede">The short list I'd give a friend for the shop, the garage and the house. Specs checked against the maker, and the catch spelled out before you buy.</p>
    <div class="cta-row">
      <a class="btn lg" href="{deal_href}" data-deal-cta data-alt-href="picks/" data-alt-text="Browse all picks">Shop Black Friday picks{icon('arrow', 'i sm')}</a>
      <a class="lnk big" href="picks/">Or browse all {N_PRODUCTS} picks{icon('arrow', 'i sm')}</a>
    </div>
    <p class="quiet">No paid placements · Same price on Amazon · Updated {e(S['updated'])}</p>
  </div>
  <div class="hh-art" aria-hidden="true">
    <div class="big-vial"><span class="bv-line l"></span><span class="bv-line r"></span><span class="bv-bubble"></span></div>
  </div>
</section>

<section class="sect" id="categories">
  <h2 class="h2">Shop by category</h2>
  <nav class="catflow" aria-label="Categories">{cats}</nav>
</section>

<section class="sect">
  <div class="sect-head"><h2 class="h2">This week's top picks</h2><a class="lnk" href="picks/">See all {N_PRODUCTS}{icon('arrow', 'i sm')}</a></div>
  <div class="cards">{''.join(card(p, up, 'home-top') for p in feats)}</div>
</section>
{spot_html}
{how_i_pick(up)}
{follow_block(up)}
{books_teaser(up)}
<section class="sect">
  <div class="sect-head"><h2 class="h2">Every guide</h2><a class="lnk" href="guides/">Browse by category{icon('arrow', 'i sm')}</a></div>
  <div class="gls">{guide_list}</div>
</section>"""
    write("index.html", page(f'{S["name"]}: Honest picks. Perfectly level.',
                             "Shop, garage, tech and gift picks checked against the maker's specs, with the catch spelled out before you buy.",
                             body, 0, "home", ""))


def picks_page():
    up = "../"
    chips = '<button class="chip" data-f="all" aria-pressed="true">All <small>' + str(N_PRODUCTS) + '</small></button>' + "".join(
        f'<button class="chip" data-f="{c["slug"]}" aria-pressed="false" style="--c:{c["color"]}">{icon(c["icon"], "i sm")}{e(c["name"])} <small>{sum(1 for p in PRODUCTS if p["_cat"] is c)}</small></button>'
        for c in CATS)
    ordered = sorted(PRODUCTS, key=lambda p: (p.get("featured", 99),))
    body = f"""
<section class="hero">
  {crumbs([("Home", up), ("All picks", None)])}
  <div class="meta"><span class="dot"></span>{N_PRODUCTS} picks · Updated {e(S['updated'])}</div>
  <h1>Every pick,<em>on one level shelf.</em></h1>
  <p class="lede">Filter by category or search by name. Tap a pick for the full specs and the catch, or go straight to Amazon.</p>
  <p class="disc">{e(DISCLOSURE)}</p>
</section>
<section class="finder" id="search">
  <label class="search">{icon('search')}<input type="search" placeholder="Search picks: helmet, drill, Kindle…" aria-label="Search picks" data-q></label>
  <div class="chips" role="group" aria-label="Filter by category">{chips}</div>
</section>
<p class="count" data-count-out aria-live="polite">{N_PRODUCTS} picks</p>
<div class="cards all" data-grid>{''.join(card(p, up, 'all-picks') for p in ordered)}</div>
<div class="empty" data-empty hidden>
  <h2>Nothing on the shelf for that <em>yet.</em></h2>
  <p>Try a shorter word, or browse the guides. New picks go up all week.</p>
  <div class="cta-row"><button class="btn" data-reset>Show every pick</button><a class="btn ghost" href="../guides/">Browse guides</a></div>
</div>"""
    write("picks/index.html", page(f'All picks | {S["name"]}', "Every Level Picks product in one place. Filter by category, search by name, and see the catch before you buy.",
                                   body, 1, "picks", "picks/"))


def compare_table(g):
    c = g.get("compare")
    if not c:
        return ""
    head = "".join(f"<th>{e(x)}</th>" for x in c["cols"])
    rows = "".join("<tr>" + "".join(f"<td>{e(x)}</td>" for x in r) + "</tr>" for r in c["rows"])
    return f"""
<section class="sect block rv" id="compare">
  <h2 class="sec">Side <em>by side</em></h2>
  <div class="tablewrap"><table class="compare"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>
  <p class="hint">Swipe the table sideways on a phone.</p>
</section>"""


def guide_page(g):
    up = "../../"
    c = CAT_OF[g["slug"]]
    n = len(g["products"])
    cards = []
    for i, p in enumerate(g["products"], 1):
        specs = "".join(f"<li>{e(s)}</li>" for s in p["specs"])
        cards.append(f"""
<article class="pick rv" id="pick-{i}" style="--c:{c['color']}">
  <div class="pick-art"><a href="{up}p/{p['_slug']}/" tabindex="-1" aria-hidden="true">{art(p, up, 'lg')}</a><span class="num">{i:02d}</span></div>
  <div class="pick-body">
    <span class="badge">{e(p["badge"])}</span>
    <h2><a href="{up}p/{p['_slug']}/">{e(p["name"])}</a></h2>
    <p class="sum">{e(p["summary"])}</p>
    <div class="specs"><h3>Key specs</h3><ul>{specs}</ul></div>
    <div class="fit">
      <div class="good"><h3>Good for</h3><p>{e(p["good_for"])}</p></div>
      <div class="watch"><h3>Watch for</h3><p>{e(p["watch_for"])}</p></div>
    </div>
    <div class="cta-row">{buy_btn(p, "btn", False, "guide")}<a class="lnk" href="{up}p/{p['_slug']}/">Full details{icon('arrow', 'i sm')}</a></div>
    <p class="aff">Affiliate link · opens Amazon · same price for you</p>
  </div>
</article>""")
    quick = "".join(f"""
    <a class="qp" href="#pick-{i}"><span class="qn">{i:02d}</span><span><b>{e(p["badge"])}</b>{e(p["name"])}</span></a>"""
                    for i, p in enumerate(g["products"], 1))
    look = "".join(f"<li>{e(x)}</li>" for x in g["what_to_look_for"])
    others = [GUIDES[s] for s in c["guides"] if s != g["slug"] and s in GUIDES]
    others += [o for o in S["guides"] if o is not g and o not in others]
    minis = "".join(f"""
    <a class="mini rv" href="../{o['slug']}/" style="--c:{CAT_OF[o['slug']]['color']}">
      <span class="k">{e(CAT_OF[o['slug']]['name'])}</span>
      <strong>{styled_title(o['title'])}</strong>
      <span class="go">{plural(len(o['products']), 'pick')}{icon('arrow', 'i sm')}</span>
    </a>""" for o in others[:3])
    body = f"""
<section class="hero" style="--c:{c['color']}">
  {crumbs([("Home", up), ("Guides", up + "guides/"), (g.get("short") or plain_title(g["title"]), None)])}
  <div class="meta"><span class="cat-pill">{icon(c['icon'], 'i sm')}{e(c['name'])}</span>{plural(n, "pick")} · Updated {e(S["updated"])}</div>
  <h1>{styled_title(g["title"])}</h1>
  <p class="lede">{e(g["intro"])}</p>
  <p class="disc">{e(DISCLOSURE)}</p>
</section>
{'<section class="sect block quick rv" aria-label="Quick picks"><h2 class="sec">Quick <em>picks</em></h2><div class="qps">' + quick + '</div></section>' if n > 1 else ''}
{compare_table(g)}
<section class="picks">{''.join(cards)}</section>
<section class="sect block look rv">
  <h2 class="sec">What to <em>look for</em></h2>
  <ul class="checks">{look}</ul>
</section>
<section class="sect">
  <div class="sect-head"><span class="k">Keep browsing</span><h2>More <em>guides.</em></h2><a class="lnk" href="../">All guides{icon('arrow', 'i sm')}</a></div>
  <div class="minis">{minis}</div>
</section>"""
    ld = crumb_ld([("Home", ""), ("Guides", "guides/"), (plain_title(g["title"]), f"guides/{g['slug']}/")])
    write(f"guides/{g['slug']}/index.html",
          page(f'{g["title"]} | {S["name"]}', g["intro"], body, 2, "deals" if g["slug"] == (S.get("promo") or {}).get("guide") else "guides",
               f"guides/{g['slug']}/", ld))


def product_page(p):
    up = "../../"
    g, c = p["_guide"], p["_cat"]
    specs = "".join(f"<li>{icon('check', 'i sm')}<span>{e(s)}</span></li>" for s in p["specs"])
    vid = ""
    yt = youtube_id(p.get("video"))
    if yt:
        vid = f"""
<section class="sect block video rv">
  <h2 class="sec">Watch it <em>in action</em></h2>
  <div class="frame"><iframe src="https://www.youtube-nocookie.com/embed/{yt}" title="{e(p['name'])} video" loading="lazy" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>
</section>"""
    elif p.get("video"):
        vid = f"""
<section class="sect block video rv">
  <h2 class="sec">Watch it <em>in action</em></h2>
  <a class="btn ghost" href="{e(p['video'])}" target="_blank" rel="noopener">{icon('play', 'i sm')}Watch the video</a>
</section>"""
    rel = "".join(card(q, up, "related") for q in related(p))
    body = f"""
<section class="pp" style="--c:{c['color']}">
  {crumbs([("Home", up), (c["name"], f"{up}picks/#{c['slug']}"), (g.get("short") or plain_title(g["title"]), f"{up}guides/{g['slug']}/"), (p["name"], None)])}
  <div class="pp-grid">
    <div class="pp-art">{art(p, up, 'xl')}</div>
    <div class="pp-info">
      <span class="badge">{e(p['badge'])}</span>
      <h1 class="pp-h">{e(p['name'])}</h1>
      <p class="sum">{e(p['summary'])}</p>
      <div class="pp-buy" data-main-buy>
        {buy_btn(p, "btn lg", False, "product")}
        <p class="aff">{icon('shield', 'i sm')}Affiliate link. Amazon shows today's price, and you pay the same.</p>
      </div>
      <div class="fit">
        <div class="good"><h3>Good for</h3><p>{e(p['good_for'])}</p></div>
        <div class="watch"><h3>Watch for</h3><p>{e(p['watch_for'])}</p></div>
      </div>
    </div>
  </div>
</section>
{vid}
<section class="sect block rv">
  <h2 class="sec">Key <em>specs</em></h2>
  <ul class="spec-list">{specs}</ul>
  <p class="hint show">From the manufacturer's and retailer's listings. Check the Amazon page for the exact model and today's price.</p>
</section>
<section class="sect block guide-link rv" style="--c:{c['color']}">
  <div><span class="k">From the guide</span><h2>{styled_title(g['title'])}</h2><p>{e(g['intro'])}</p></div>
  <a class="btn ghost" href="{up}guides/{g['slug']}/">{'Compare all ' + str(len(g['products'])) + ' picks' if len(g['products']) > 1 else 'Read the full guide'}{icon('arrow', 'i sm')}</a>
</section>
{how_i_pick(up, True)}
<section class="sect">
  <div class="sect-head"><span class="k">Not the one?</span><h2>You might <em>also like.</em></h2><a class="lnk" href="{up}picks/">All picks{icon('arrow', 'i sm')}</a></div>
  <div class="cards">{rel}</div>
</section>"""
    sticky = f"""<div class="buybar" data-buybar style="--c:{c['color']}"><div class="bb-in"><span class="bb-name">{e(p['name'])}</span>{buy_btn(p, "btn sm", True, "sticky")}</div></div>"""
    ld = crumb_ld([("Home", ""), (plain_title(g["title"]), f"guides/{g['slug']}/"), (p["name"], f"p/{p['_slug']}/")])
    write(f"p/{p['_slug']}/index.html",
          page(f'{p["name"]}: {p["badge"]} | {S["name"]}', p["summary"], body, 2, None, f"p/{p['_slug']}/", ld, sticky))


def guides_index():
    up = "../"
    sections = []
    n = 0
    for c in CATS:
        tiles = []
        for gs in c["guides"]:
            g = GUIDES.get(gs)
            if not g:
                continue
            n += 1
            tiles.append(f"""
<a class="tile rv" href="{g['slug']}/" style="--c:{c['color']}">
  <span class="tn">{n:02d}</span>
  <span class="k">{e(g.get('short') or 'Guide')}</span>
  <h3>{styled_title(g["title"])}</h3>
  <p>{e(g["intro"])}</p>
  <span class="go">{plural(len(g["products"]), "pick")}{icon('arrow', 'i sm')}</span>
</a>""")
        sections.append(f"""
<section class="sect" id="{c['slug']}" style="--c:{c['color']}">
  <div class="sect-head"><span class="cat-pill">{icon(c['icon'], 'i sm')}{e(c['name'])}</span><p class="sect-blurb">{e(c['blurb'])}</p></div>
  <div class="tiles">{''.join(tiles)}</div>
</section>""")
    jump = "".join(f'<a href="#{c["slug"]}" style="--c:{c["color"]}">{icon(c["icon"], "i sm")}{e(c["name"])}</a>' for c in CATS)
    body = f"""
<section class="hero">
  {crumbs([("Home", up), ("Guides", None)])}
  <div class="meta"><span class="dot"></span>{plural(N_GUIDES, "guide")} · Updated {e(S["updated"])}</div>
  <h1>Every guide,<em>sorted by shelf.</em></h1>
  <p class="lede">Each guide is a short list with a side-by-side, what to look for and the catch on every pick.</p>
  <nav class="jump" aria-label="Jump to category">{jump}</nav>
</section>
{''.join(sections)}
{books_teaser(up)}"""
    write("guides/index.html", page(f'All guides | {S["name"]}', S["tagline"], body, 1, "guides", "guides/"))


def books_page():
    up = "../"
    blocks = []
    for b in S.get("books", []):
        soon = b.get("status") != "available"
        inside = "".join(f"<li>{e(x)}</li>" for x in b.get("inside", []))
        action = (f'<a class="btn lg" href="{e(b["url"])}" target="_blank" rel="noopener">Get the book{icon("out", "i sm")}</a>' if not soon
                  else f'<p class="soon">{icon("check", "i sm")}In the works. Follow along to hear the day it drops.</p><div class="socs big">{socials()}</div>')
        blocks.append(f"""
<section class="sect book rv">
  <div class="bt-cover lg" aria-hidden="true"><span class="bt-k">Level Picks</span><strong>{e(b['title'])}</strong><span class="bt-v"><span class="vial"><i></i></span></span></div>
  <div>
    <span class="k">{'Coming soon' if soon else 'Available now'}</span>
    <h2>{e(b['title'])}</h2>
    <p class="lede">{e(b['pitch'])}</p>
    <h3 class="inside">What's inside</h3>
    <ul class="checks">{inside}</ul>
    {action}
  </div>
</section>""")
    body = f"""
<section class="hero">
  {crumbs([("Home", up), ("Books", None)])}
  <div class="meta"><span class="dot"></span>Level Picks books</div>
  <h1>Buying guides <em>you can keep.</em></h1>
  <p class="lede">The site gives you the short list. The books give you the whole job: the best, the budget and the bare minimum, how it all goes together, and what to skip so you don't buy twice.</p>
</section>
{''.join(blocks)}
<section class="sect block rv">
  <h2 class="sec">Every book <em>covers</em></h2>
  <ul class="checks">
    <li>Three tiers for every budget: best, budget and the bare minimum that still works</li>
    <li>What every part or tool does, in plain words</li>
    <li>Step-by-step how-to, with the mistakes people make</li>
    <li>The catch on each pick, same as the site</li>
  </ul>
</section>
<section class="sect">
  <div class="sect-head"><span class="k">Shopping today?</span><h2>The picks are <em>live now.</em></h2></div>
  <div class="cta-row"><a class="btn" href="../picks/">Browse all {N_PRODUCTS} picks{icon('arrow', 'i sm')}</a><a class="btn ghost" href="../guides/">See every guide</a></div>
</section>"""
    write("books/index.html", page(f'Buying-guide books | {S["name"]}', "Level Picks books: full buying guides with best, budget and bare-minimum picks and step-by-step how-tos.",
                                   body, 1, "books", "books/"))


def about_page():
    up = "../"
    body = f"""
<section class="hero">
  {crumbs([("Home", up), ("About", None)])}
  <div class="meta"><span class="dot"></span>About Level Picks</div>
  <h1>A fabricator's <em>short list.</em></h1>
  <p class="lede">Level Picks is run by a small fab-shop owner in Georgia. I spend my days around tools that have to work, so I pick gear the same way: what it's for, what it can't do, and whether it's worth the money.</p>
</section>
<section class="sect block prose rv">
  <p>The guides cover shop tools, car and garage gear, tech, gifts and the deals worth knowing about. Specs come from manufacturer and retailer listings, and every pick says what to watch out for. No brand pays to be on a list.</p>
  <p>I'm filming hands-on videos of the gear I own. When a pick has one, its page shows it. Specs change when manufacturers update a model, and the guides get updated when that happens.</p>
</section>
{how_i_pick(up, True)}
{follow_block(up)}
<section class="sect">
  <div class="sect-head"><span class="k">Ready to look?</span><h2>Start <em>shopping.</em></h2></div>
  <div class="cta-row"><a class="btn" href="../picks/">Browse all {N_PRODUCTS} picks{icon('arrow', 'i sm')}</a><a class="btn ghost" href="../guides/">See every guide</a></div>
</section>"""
    write("about/index.html", page(f'About | {S["name"]}', "Who runs Level Picks and how picks are chosen.", body, 1, "about", "about/"))


def simple(slug, title, paras):
    up = "../"
    body = f"""
<section class="hero slim">
  {crumbs([("Home", up), (title, None)])}
  <h1>{e(title)}</h1>
</section>
<article class="sect block prose rv">{''.join(f"<p>{e(x)}</p>" for x in paras)}</article>
<section class="sect"><div class="cta-row"><a class="btn" href="../picks/">Browse all picks{icon('arrow', 'i sm')}</a><a class="btn ghost" href="../">Back to home</a></div></section>"""
    write(f"{slug}/index.html", page(f'{title} | {S["name"]}', paras[0], body, 1, None, f"{slug}/"))


def not_found():
    feats = sorted([p for p in PRODUCTS if p.get("featured")], key=lambda p: p["featured"])[:3]
    body = f"""
<section class="hero">
  <div class="meta"><span class="dot"></span>404</div>
  <h1>That page is <em>off level.</em></h1>
  <p class="lede">The link may be old, or the pick moved. Here's where to go next.</p>
  <div class="cta-row"><a class="btn" href="/picks/">Browse all picks{icon('arrow', 'i sm')}</a><a class="btn ghost" href="/">Go home</a></div>
</section>
<section class="sect">
  <div class="sect-head"><span class="k">Popular</span><h2>Top <em>picks.</em></h2></div>
  <div class="cards">{''.join(card(p, '/', '404') for p in feats)}</div>
</section>"""
    html_ = page(f'Page not found | {S["name"]}', "This page moved. Browse every Level Picks pick.", body, 0, None, "404.html")
    write("404.html", html_.replace('href="style.css"', 'href="/style.css"').replace('href="brand/', 'href="/brand/')
          .replace('href="picks/', 'href="/picks/').replace('href="guides/', 'href="/guides/').replace('href="books/', 'href="/books/')
          .replace('href="about/', 'href="/about/').replace('href="disclosure/', 'href="/disclosure/').replace('href="privacy/', 'href="/privacy/')
          .replace('href="p/', 'href="/p/').replace('href="" aria-label', 'href="/" aria-label').replace('class="brand" href=""', 'class="brand" href="/"'))


JS = r"""
(function(){
  var root=document.documentElement, bar=document.querySelector('.progress b'),
      bub=document.querySelector('.top .vial i'), top=document.querySelector('.top');
  function onScroll(){
    var h=root.scrollHeight-innerHeight, p=h>0?Math.min(1,scrollY/h):0;
    if(bar) bar.style.transform='scaleX('+p+')';
    if(bub) bub.style.transform='translateX('+(p*14-7)+'px)';
    top.classList.toggle('scrolled',scrollY>8);
  }
  addEventListener('scroll',onScroll,{passive:true}); onScroll();
  var setStick=function(){root.style.setProperty('--stick',(top.offsetHeight+8)+'px');};
  addEventListener('resize',setStick); setStick();

  // promo countdown: shows until the end date, then hides itself and retires deal links
  var promo=document.querySelector('.promo');
  if(promo){
    var end=new Date(promo.getAttribute('data-ends')).getTime(), out=promo.querySelector('[data-count]');
    var tick=function(){
      var ms=end-Date.now();
      if(!(ms>0)){promo.hidden=true;
        document.querySelectorAll('[data-deal-cta]').forEach(function(a){a.href=a.getAttribute('data-alt-href');a.firstChild.textContent=a.getAttribute('data-alt-text');});
        return false;}
      if(promo.hidden){promo.hidden=false;setTimeout(function(){window.dispatchEvent(new Event('resize'));},0);}
      var d=Math.floor(ms/864e5), h=Math.floor(ms%864e5/36e5), m=Math.floor(ms%36e5/6e4);
      out.textContent=(d?d+'d ':'')+h+'h '+(d?'':m+'m ')+'left';
      return true;
    };
    if(tick()) setInterval(tick,30000);
  }

  // close the mobile menu after tapping a link inside it
  document.querySelectorAll('.menu a').forEach(function(a){a.addEventListener('click',function(){var d=a.closest('details');if(d)d.open=false;});});

  // count clicks out to Amazon
  document.addEventListener('click',function(ev){
    var a=ev.target.closest&&ev.target.closest('a[data-buy]'); if(!a) return;
    (window.dataLayer=window.dataLayer||[]).push({event:'amazon_click',product:a.getAttribute('data-buy'),placement:a.getAttribute('data-where'),page:location.pathname});
  });

  // sticky buy bar on product pages
  var bb=document.querySelector('[data-buybar]'), mb=document.querySelector('[data-main-buy]');
  if(bb&&mb&&'IntersectionObserver' in window){
    new IntersectionObserver(function(es){bb.classList.toggle('on',!es[0].isIntersecting&&es[0].boundingClientRect.top<0);}).observe(mb);
  }

  // all-picks filter + search
  var grid=document.querySelector('[data-grid]');
  if(grid){
    var cards=[].slice.call(grid.children), q=document.querySelector('[data-q]'), chips=[].slice.call(document.querySelectorAll('.chip')),
        out=document.querySelector('[data-count-out]'), empty=document.querySelector('[data-empty]'), f='all';
    var apply=function(){
      var t=(q.value||'').trim().toLowerCase(), n=0;
      cards.forEach(function(c){var ok=(f==='all'||c.getAttribute('data-cat')===f)&&(!t||c.getAttribute('data-text').indexOf(t)>-1);c.hidden=!ok;if(ok){n++;c.classList.add('in');}});
      out.textContent=n+(n===1?' pick':' picks'); empty.hidden=n>0;
      chips.forEach(function(ch){ch.setAttribute('aria-pressed',ch.getAttribute('data-f')===f?'true':'false');});
    };
    var setF=function(v){f=chips.some(function(c){return c.getAttribute('data-f')===v;})?v:'all';apply();};
    chips.forEach(function(ch){ch.addEventListener('click',function(){setF(ch.getAttribute('data-f'));history.replaceState(null,'',f==='all'?location.pathname:'#'+f);});});
    q.addEventListener('input',apply);
    var r=document.querySelector('[data-reset]'); if(r) r.addEventListener('click',function(){q.value='';setF('all');});
    var fromHash=function(){var h=location.hash.slice(1);if(h==='search'){q.focus();}else if(h){setF(h);}};
    addEventListener('hashchange',fromHash); fromHash();
  }

  // reveal on scroll
  var els=document.querySelectorAll('.rv');
  if(!('IntersectionObserver' in window)){els.forEach(function(x){x.classList.add('in')});return;}
  var io=new IntersectionObserver(function(es){es.forEach(function(en){
    if(en.isIntersecting){en.target.classList.add('in');io.unobserve(en.target);}});},{rootMargin:'0px 0px -6% 0px'});
  els.forEach(function(x){io.observe(x)});
})();
"""

CSS = r"""
:root{--bg:#070b16;--bg2:#0b1222;--bg3:#101a30;--ink:#f4f1ea;--ink2:#d7dcea;--mute:#a9b2c6;--amber:#ffc531;--lime:#9be15d;--peach:#ffb38f;
--line:rgba(255,255,255,.12);--line2:rgba(255,255,255,.06);--glass:rgba(16,22,40,.6);--glass2:rgba(255,255,255,.035);
--sans:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;--serif:"Instrument Serif",Georgia,serif;
--pad:clamp(16px,4vw,48px);--max:1160px;--r:24px;--c:var(--amber);--ease:cubic-bezier(.2,.8,.2,1)}
*{box-sizing:border-box;margin:0;padding:0}
html{background:var(--bg);color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased;scroll-behavior:smooth;scroll-padding-top:120px}
body{min-height:100vh;font-size:16px;line-height:1.6;overflow-x:hidden;background:var(--bg)}
.glow{position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(1100px 650px at 85% -5%,rgba(255,197,49,.13),transparent 60%),
             radial-gradient(900px 600px at -10% 35%,rgba(155,225,93,.08),transparent 60%),
             radial-gradient(800px 600px at 110% 85%,rgba(120,140,255,.08),transparent 60%)}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.05;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);
  background-size:64px 64px;mask-image:radial-gradient(ellipse 80% 60% at 50% 0%,#000 30%,transparent 75%);-webkit-mask-image:radial-gradient(ellipse 80% 60% at 50% 0%,#000 30%,transparent 75%)}
main,.foot{position:relative;z-index:1}
::selection{background:var(--amber);color:#111}
a{color:var(--amber)}
:focus-visible{outline:2px solid var(--amber);outline-offset:3px;border-radius:8px}
em{font-family:var(--serif);font-style:italic;font-weight:400;color:var(--amber);letter-spacing:-.005em}
.i{width:20px;height:20px;flex:none}.i.sm{width:16px;height:16px}.i.big{width:44px;height:44px}
.skip{position:absolute;left:-999px;top:8px;z-index:99;background:var(--amber);color:#111;padding:10px 14px;border-radius:10px;font-weight:700}
.skip:focus{left:8px}
.k{display:inline-block;font-size:11.5px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--c)}
[hidden]{display:none!important}

/* header */
.top{position:sticky;top:0;z-index:40;background:rgba(7,11,22,.78);backdrop-filter:blur(16px) saturate(140%);-webkit-backdrop-filter:blur(16px) saturate(140%);border-bottom:1px solid transparent;transition:border-color .3s,background .3s}
.top.scrolled{border-bottom-color:var(--line);background:rgba(7,11,22,.9)}
.promo{display:flex;align-items:center;justify-content:center;gap:10px;padding:9px var(--pad);font-size:13px;color:#14110a;text-decoration:none;
  background:linear-gradient(90deg,#ffc531,#ffd977 50%,#ffc531);background-size:200% 100%;animation:sheen 6s linear infinite;font-weight:500}
.promo b{font-weight:800}.promo .sep{opacity:.5}.promo .dot{background:#14110a;box-shadow:none}
.promo-go{display:inline-flex;align-items:center;gap:6px;font-weight:700;margin-left:6px;text-decoration:underline;text-underline-offset:3px}
@keyframes sheen{to{background-position:-200% 0}}
.bar{max-width:var(--max);margin:0 auto;display:flex;align-items:center;gap:14px;padding:calc(10px + env(safe-area-inset-top)) var(--pad) 10px}
.brand{display:inline-flex;align-items:center;gap:12px;color:var(--ink);text-decoration:none;font-weight:800;letter-spacing:.22em;font-size:13px;text-transform:uppercase;white-space:nowrap}
.vial{width:42px;height:18px;border:2.5px solid var(--amber);border-radius:12px;background:rgba(155,225,93,.22);position:relative;flex:none;box-shadow:0 0 18px -6px rgba(255,197,49,.6)}
.vial::before,.vial::after{content:"";position:absolute;top:-2.5px;bottom:-2.5px;width:1.5px;background:var(--amber);opacity:.8}
.vial::before{left:12px}.vial::after{right:12px}
.vial i{position:absolute;top:3px;left:13px;width:12px;height:7px;border-radius:50%;background:#fff;box-shadow:0 0 8px rgba(255,255,255,.7);transition:transform .15s linear}
.links{display:flex;gap:2px;margin-left:auto}
.links a,.sheet nav a{color:var(--mute);text-decoration:none;font-size:14px;font-weight:500;padding:8px 13px;border-radius:999px;transition:color .2s,background .2s}
.links a:hover,.links a[aria-current]{color:var(--ink);background:rgba(255,255,255,.07)}
.links a[data-deal]{color:var(--amber)}
.bar-r{display:flex;align-items:center;gap:8px}
.search-btn{display:inline-flex;align-items:center;gap:8px;color:var(--ink2);text-decoration:none;font-size:13.5px;font-weight:500;padding:8px 14px;border-radius:999px;border:1px solid var(--line);background:var(--glass2);transition:border-color .2s}
.search-btn:hover{border-color:rgba(255,197,49,.5)}
.menu{display:none;position:relative}
.menu summary{list-style:none;cursor:pointer;display:grid;place-items:center;width:42px;height:42px;border-radius:12px;border:1px solid var(--line);color:var(--ink);background:var(--glass2)}
.menu summary::-webkit-details-marker{display:none}
.menu .shut,.menu[open] .open{display:none}.menu[open] .shut{display:block}
.sheet{position:absolute;right:0;top:52px;width:min(330px,calc(100vw - 32px));padding:14px;border-radius:20px;border:1px solid var(--line);background:#0c1324;box-shadow:0 30px 60px -20px rgba(0,0,0,.8);display:grid;gap:12px}
.sheet nav{display:grid;gap:2px}.sheet nav a{font-size:16px;padding:11px 14px}
.sheet nav a[aria-current]{background:rgba(255,255,255,.07);color:var(--ink)}
.sheet-cats{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding-top:12px;border-top:1px solid var(--line)}
.sheet-cats a{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--ink2);text-decoration:none;padding:10px;border-radius:12px;background:color-mix(in srgb,var(--c) 10%,transparent)}
.sheet-cats .i{color:var(--c);width:18px;height:18px}
.progress{position:absolute;left:0;right:0;bottom:-1px;height:2px}
.progress b{display:block;height:100%;background:linear-gradient(90deg,var(--lime),var(--amber));transform-origin:0 50%;transform:scaleX(0)}

/* layout */
main{max-width:var(--max);margin:0 auto;padding:0 var(--pad) 40px}
.sect{margin-top:clamp(48px,7vw,88px)}
.sect-head{display:flex;flex-wrap:wrap;align-items:flex-end;gap:6px 18px;margin-bottom:22px}
.sect-head .k{flex-basis:100%}
.sect-head h2,.sec{font-weight:800;font-size:clamp(26px,3.4vw,40px);letter-spacing:-.025em;line-height:1.05}
.sec{font-size:clamp(22px,2.4vw,30px);margin-bottom:18px}
.sect-head .lnk{margin-left:auto}
.sect-blurb{color:var(--mute);font-size:15px}
.lnk{display:inline-flex;align-items:center;gap:6px;font-size:14.5px;font-weight:600;text-decoration:none;color:var(--amber)}
.lnk .i{transition:transform .25s}.lnk:hover .i{transform:translateX(3px)}
.block{background:var(--glass);border:1px solid var(--line);border-radius:var(--r);padding:clamp(20px,3vw,34px);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.cta-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center}

/* hero (inner pages) */
.hero{padding:clamp(34px,6vw,72px) 0 10px;max-width:880px}
.hero.slim{padding-bottom:0}
.crumbs{font-size:13px;color:var(--mute);margin-bottom:18px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.crumbs a{color:var(--mute);text-decoration:none}.crumbs a:hover{color:var(--ink)}
.crumbs i{opacity:.45;font-style:normal}.crumbs span{color:var(--ink2)}
.meta{display:flex;align-items:center;gap:10px;font-size:11.5px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--amber);margin-bottom:18px}
.cat-pill{display:inline-flex;align-items:center;gap:7px;font-size:11.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--c);padding:6px 11px;border-radius:999px;border:1px solid color-mix(in srgb,var(--c) 45%,transparent);background:color-mix(in srgb,var(--c) 10%,transparent)}
.dot{width:7px;height:7px;border-radius:50%;background:var(--lime);box-shadow:0 0 12px var(--lime);animation:pulse 2.6s ease-in-out infinite;flex:none}
@keyframes pulse{50%{opacity:.45}}
h1{font-weight:800;font-size:clamp(36px,6vw,68px);line-height:1.02;letter-spacing:-.035em;text-wrap:balance}
h1 em{display:block;margin-top:.1em;font-size:.88em;line-height:1.08}
.lede{margin-top:20px;max-width:62ch;font-size:clamp(17px,1.5vw,19.5px);line-height:1.6;color:#c9cfdc}
.lede b{color:var(--ink);font-weight:600}
.disc{margin-top:14px;font-size:12.5px;color:var(--mute)}

/* buttons */
.btn{white-space:nowrap;display:inline-flex;align-items:center;justify-content:center;gap:10px;font:700 15px/1 var(--sans);text-decoration:none;color:#14110a;background:var(--amber);border:1px solid var(--amber);border-radius:999px;padding:15px 22px;cursor:pointer;box-shadow:0 12px 32px -12px rgba(255,197,49,.7);transition:transform .25s var(--ease),background .25s,border-color .25s}
.btn:hover{background:#ffd462;transform:translateY(-2px)}
.btn.lg{padding:18px 26px;font-size:16px}
.btn.sm{padding:11px 16px;font-size:14px;gap:7px}
.btn.ghost{background:var(--glass2);color:var(--ink);border-color:var(--line);box-shadow:none}
.btn.ghost:hover{border-color:rgba(255,197,49,.55);background:rgba(255,197,49,.07)}
.aff{display:flex;align-items:center;gap:7px;margin-top:10px;font-size:12.5px;color:var(--mute)}

/* home hero */
.home-hero{display:grid;grid-template-columns:1.15fr .85fr;gap:40px;align-items:center;padding:clamp(36px,6vw,80px) 0 10px}
.home-hero h1{font-size:clamp(44px,7.2vw,92px)}
.home-hero .cta-row{margin-top:28px}
.trust{list-style:none;display:flex;flex-wrap:wrap;gap:10px 22px;margin-top:24px}
.trust li{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--ink2)}
.trust .i{color:var(--lime)}
.hh-art{position:relative;aspect-ratio:1/1;max-width:460px;width:100%;justify-self:center}
.big-vial{position:absolute;left:4%;right:4%;top:40%;height:22%;border:6px solid var(--amber);border-radius:999px;
  background:linear-gradient(180deg,rgba(155,225,93,.38),rgba(155,225,93,.14));box-shadow:0 0 80px -10px rgba(255,197,49,.55),inset 0 6px 14px rgba(255,255,255,.12);transform:rotate(-8deg);animation:tilt 7s ease-in-out infinite}
.bv-line{position:absolute;top:-6px;bottom:-6px;width:4px;background:var(--amber)}
.bv-line.l{left:37%}.bv-line.r{right:37%}
.bv-bubble{position:absolute;top:22%;left:50%;width:22%;height:56%;margin-left:-11%;border-radius:50%;background:radial-gradient(circle at 35% 35%,#fff,#e9f2e4 60%,#c9d6c2);box-shadow:0 0 30px rgba(255,255,255,.6);animation:bubble 7s ease-in-out infinite}
@keyframes tilt{0%,100%{transform:rotate(-8deg)}50%{transform:rotate(-2deg)}}
@keyframes bubble{0%,100%{transform:translateX(-90%)}50%{transform:translateX(0)}}
.float{position:absolute;display:flex;align-items:center;gap:10px;padding:10px 14px 10px 10px;border-radius:16px;text-decoration:none;color:var(--ink);font-size:13.5px;font-weight:600;
  background:rgba(13,20,38,.85);border:1px solid color-mix(in srgb,var(--c) 45%,transparent);box-shadow:0 20px 40px -18px rgba(0,0,0,.8);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);animation:bob 6s ease-in-out infinite;transition:border-color .25s}
.float:hover{border-color:var(--c)}
.float span{max-width:210px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.float .i{width:34px;height:34px;padding:7px;border-radius:10px;color:var(--c);background:color-mix(in srgb,var(--c) 16%,transparent)}
.float.f1{left:0;top:6%}.float.f2{right:0;top:22%;animation-delay:-2s}.float.f3{left:12%;bottom:8%;animation-delay:-4s}
@keyframes bob{50%{transform:translateY(-10px)}}

/* category tiles */
.cats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.cat{position:relative;overflow:hidden;display:flex;flex-direction:column;gap:8px;padding:24px;border-radius:var(--r);text-decoration:none;color:var(--ink);
  border:1px solid var(--line);background:linear-gradient(160deg,color-mix(in srgb,var(--c) 14%,transparent),transparent 55%),var(--glass);transition:transform .3s var(--ease),border-color .3s}
.cat::after{content:"";position:absolute;right:-60px;top:-60px;width:180px;height:180px;border-radius:50%;background:radial-gradient(circle,color-mix(in srgb,var(--c) 26%,transparent),transparent 65%);transition:transform .5s var(--ease)}
.cat:hover{transform:translateY(-4px);border-color:color-mix(in srgb,var(--c) 60%,transparent)}
.cat:hover::after{transform:scale(1.25)}
.cat-i{display:grid;place-items:center;width:48px;height:48px;border-radius:14px;color:var(--c);background:color-mix(in srgb,var(--c) 15%,transparent);border:1px solid color-mix(in srgb,var(--c) 35%,transparent);margin-bottom:6px}
.cat-i .i{width:26px;height:26px}
.cat h3{font-size:20px;font-weight:800;letter-spacing:-.015em}
.cat p{font-size:14.5px;color:var(--mute);line-height:1.5}
.go{margin-top:auto;padding-top:6px;display:inline-flex;align-items:center;gap:6px;font-size:13.5px;font-weight:700;color:var(--c)}
.go .i{transition:transform .25s}
.cat:hover .go .i,.tile:hover .go .i,.mini:hover .go .i{transform:translateX(4px)}

/* product art */
.art{position:relative;aspect-ratio:4/3;border-radius:18px;overflow:hidden;display:grid;place-items:center;color:var(--c);
  background:radial-gradient(circle at 50% 60%,color-mix(in srgb,var(--c) 30%,transparent),transparent 62%),linear-gradient(160deg,#121b31,#0a1020);border:1px solid color-mix(in srgb,var(--c) 22%,transparent)}
.art::before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:22px 22px;mask-image:radial-gradient(circle,#000,transparent 75%);-webkit-mask-image:radial-gradient(circle,#000,transparent 75%)}
.art img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.art-ring{position:absolute;width:56%;aspect-ratio:1;border-radius:50%;border:1px dashed color-mix(in srgb,var(--c) 45%,transparent);animation:spin 40s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.art-i{position:relative;width:38%;height:38%;stroke-width:1.2;filter:drop-shadow(0 0 18px color-mix(in srgb,var(--c) 60%,transparent));transition:transform .5s var(--ease)}
.art.lg .art-i{width:42%;height:42%}.art.xl{aspect-ratio:1/1}.art.xl .art-i{width:40%;height:40%}
.stamp{position:absolute;left:10px;bottom:10px;display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#14110a;background:var(--lime);padding:5px 9px;border-radius:999px}
.stamp .i{width:14px;height:14px}

/* product cards */
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
.card{display:flex;flex-direction:column;border-radius:var(--r);border:1px solid var(--line);background:var(--glass);overflow:hidden;transition:transform .3s var(--ease),border-color .3s}
.card:hover{transform:translateY(-4px);border-color:color-mix(in srgb,var(--c) 55%,transparent)}
.card:hover .art-i{transform:scale(1.08) rotate(-4deg)}
.card-art{display:block;padding:10px 10px 0}
.card-body{display:flex;flex-direction:column;gap:6px;padding:14px 16px 16px;flex:1}
.card-body .k{font-size:10.5px;letter-spacing:.12em}
.card h3{font-size:16.5px;line-height:1.3;font-weight:700;letter-spacing:-.01em}
.card h3 a{color:var(--ink);text-decoration:none}
.card h3 a::after{content:"";position:absolute;inset:0}
.card{position:relative}
.card-badge{font-family:var(--serif);font-style:italic;font-size:17px;color:#e8e1d2;line-height:1.2}
.card-sum{font-size:13.5px;color:var(--mute);line-height:1.5;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card-cta{margin-top:auto;padding-top:10px;display:flex;align-items:center;justify-content:space-between;gap:10px;position:relative;z-index:2}
.card-cta .lnk{font-size:13.5px}

/* spotlight */
.spot{display:grid;grid-template-columns:.8fr 1.2fr;gap:clamp(20px,4vw,48px);align-items:center;padding:clamp(18px,3vw,30px);border-radius:32px;border:1px solid color-mix(in srgb,var(--c) 35%,transparent);
  background:linear-gradient(120deg,color-mix(in srgb,var(--c) 12%,transparent),transparent 60%),var(--glass)}
.spot h2{font-size:clamp(26px,3.2vw,40px);font-weight:800;letter-spacing:-.025em;line-height:1.08;margin:8px 0 12px}
.spot h2 em,.guide-link h2 em,.tile h3 em,.mini strong em{display:block}
.spot p{color:#c9cfdc;max-width:58ch;margin-bottom:22px}

/* how I pick */
.how-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.how-i{padding:24px;border-radius:var(--r);border:1px solid var(--line);background:var(--glass)}
.how-n{display:grid;place-items:center;width:46px;height:46px;border-radius:14px;color:var(--lime);background:rgba(155,225,93,.12);border:1px solid rgba(155,225,93,.35);margin-bottom:14px}
.how-i h3{font-size:18px;font-weight:800;margin-bottom:6px}
.how-i p{font-size:15px;color:var(--mute)}

/* follow */
.follow-in{display:grid;grid-template-columns:auto 1fr;gap:clamp(18px,4vw,40px);align-items:center;padding:clamp(22px,4vw,44px);border-radius:32px;border:1px solid var(--line);
  background:radial-gradient(600px 300px at 0% 50%,rgba(255,107,139,.14),transparent 70%),radial-gradient(500px 300px at 100% 0%,rgba(79,195,247,.12),transparent 70%),var(--glass)}
.follow-art{display:grid;place-items:center;width:clamp(84px,12vw,130px);aspect-ratio:9/14;border-radius:22px;color:#fff;background:linear-gradient(160deg,#ff6b8b,#b388ff 55%,#4fc3f7);box-shadow:0 20px 50px -18px rgba(255,107,139,.7)}
.follow h2{font-size:clamp(26px,3.2vw,40px);font-weight:800;letter-spacing:-.025em;line-height:1.08;margin:8px 0 10px}
.follow p{color:#c9cfdc;max-width:56ch}
.follow .k{color:#ff8fa8}
.socs{display:flex;flex-wrap:wrap;gap:8px}
.soc{display:inline-flex;align-items:center;gap:8px;padding:9px 14px;border-radius:999px;border:1px solid var(--line);background:var(--glass2);color:var(--ink);text-decoration:none;font-size:14px;font-weight:600;transition:border-color .2s,background .2s}
.soc:hover{border-color:rgba(255,197,49,.55);background:rgba(255,197,49,.07)}
.socs.big{margin-top:20px}.socs.big .soc{padding:13px 20px;font-size:15px}

/* books */
.books-teaser,.book{display:grid;grid-template-columns:auto 1fr;gap:clamp(22px,4vw,48px);align-items:center;padding:clamp(22px,4vw,44px);border-radius:32px;border:1px solid rgba(155,225,93,.3);
  background:linear-gradient(120deg,rgba(155,225,93,.1),transparent 55%),var(--glass)}
.books-teaser h2,.book h2{font-size:clamp(26px,3.2vw,40px);font-weight:800;letter-spacing:-.025em;line-height:1.08;margin:8px 0 12px}
.books-teaser p{color:#c9cfdc;max-width:58ch;margin-bottom:20px}
.books-teaser .k,.book .k{color:var(--lime)}
.bt-cover{position:relative;width:clamp(130px,16vw,180px);aspect-ratio:3/4;border-radius:6px 14px 14px 6px;padding:18px 16px;display:flex;flex-direction:column;gap:10px;
  background:linear-gradient(160deg,#16213b,#0b1121);border:1px solid rgba(255,197,49,.5);box-shadow:-8px 0 0 -2px #0a0f1d,0 30px 60px -20px rgba(0,0,0,.9),inset 6px 0 0 rgba(255,197,49,.85);transform:rotate(-4deg);transition:transform .5s var(--ease)}
.books-teaser:hover .bt-cover,.book:hover .bt-cover{transform:rotate(0)}
.bt-cover.lg{width:clamp(150px,20vw,220px)}
.bt-k{font-size:9.5px;font-weight:800;letter-spacing:.22em;text-transform:uppercase;color:var(--amber);padding-left:6px}
.bt-cover strong{font-family:var(--serif);font-weight:400;font-style:italic;font-size:clamp(22px,2.6vw,30px);line-height:1.05;color:#f4f1ea;padding-left:6px}
.bt-v{margin-top:auto;padding-left:6px}
.inside{margin:24px 0 12px;font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--mute)}
.soon{display:flex;align-items:center;gap:8px;margin-top:24px;color:var(--lime);font-weight:600}
.book .socs.big{margin-top:12px}

/* guide list */
.gls{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.gl{display:flex;align-items:center;gap:14px;padding:14px 16px;border-radius:18px;border:1px solid var(--line);background:var(--glass2);color:var(--ink);text-decoration:none;transition:border-color .25s,background .25s}
.gl:hover{border-color:color-mix(in srgb,var(--c) 55%,transparent);background:color-mix(in srgb,var(--c) 7%,transparent)}
.gl-i{display:grid;place-items:center;width:40px;height:40px;border-radius:12px;flex:none;color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent)}
.gl b{display:block;font-size:15px;font-weight:700;line-height:1.3}
.gl small{font-size:12.5px;color:var(--mute)}
.gl>.i{margin-left:auto;color:var(--mute)}

/* all picks finder */
.finder{position:sticky;top:var(--stick,64px);z-index:20;margin-top:28px;padding:12px;border-radius:22px;border:1px solid var(--line);background:rgba(10,16,30,.9);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);display:grid;gap:10px}
.search{display:flex;align-items:center;gap:10px;padding:0 14px;border-radius:14px;border:1px solid var(--line);background:rgba(255,255,255,.04);color:var(--mute)}
.search:focus-within{border-color:rgba(255,197,49,.6)}
.search input{flex:1;min-width:0;background:none;border:0;outline:0;color:var(--ink);font:500 16px var(--sans);padding:13px 0}
.search input::placeholder{color:#7d879c}
.chips{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;display:inline-flex;align-items:center;gap:7px;font:600 13.5px var(--sans);color:var(--ink2);padding:9px 14px;border-radius:999px;border:1px solid var(--line);background:var(--glass2);cursor:pointer;transition:all .2s}
.chip small{font-size:11.5px;color:var(--mute);font-weight:600}
.chip .i{color:var(--c)}
.chip:hover{border-color:color-mix(in srgb,var(--c) 55%,transparent)}
.chip[aria-pressed=true]{background:var(--c);border-color:var(--c);color:#14110a}
.chip[aria-pressed=true] .i,.chip[aria-pressed=true] small{color:#14110a}
.count{margin:20px 2px 12px;font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}
.empty{margin-top:30px;text-align:center;padding:50px 20px;border-radius:var(--r);border:1px dashed var(--line)}
.empty h2{font-size:28px;font-weight:800;margin-bottom:8px}.empty p{color:var(--mute);margin-bottom:20px}.empty .cta-row{justify-content:center}

/* guide page */
.qps{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.qp{display:flex;gap:14px;align-items:center;text-decoration:none;color:var(--ink);padding:14px 16px;border-radius:16px;border:1px solid var(--line);background:var(--glass2);transition:transform .25s,border-color .25s,background .25s}
.qp:hover{transform:translateY(-2px);border-color:rgba(255,197,49,.45);background:rgba(255,197,49,.06)}
.qn{font-family:var(--serif);font-style:italic;font-size:30px;line-height:1;color:var(--amber);min-width:34px}
.qp b{display:block;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--lime);font-weight:600;margin-bottom:2px}
.qp span:last-child{font-size:15px;font-weight:600;line-height:1.3}
.tablewrap{overflow-x:auto;border-radius:16px;border:1px solid var(--line)}
.compare{width:100%;border-collapse:collapse;font-size:14.5px}
.compare th,.compare td{text-align:left;padding:12px 16px;white-space:nowrap}
.compare th{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--amber);font-weight:600;background:rgba(255,197,49,.06);border-bottom:1px solid var(--line)}
.compare td{border-bottom:1px solid var(--line2);color:var(--ink2)}
.compare tr:last-child td{border-bottom:0}
.compare tbody tr:hover td{background:rgba(255,255,255,.03)}
.compare td:first-child{font-weight:600;color:var(--ink);position:sticky;left:0;background:#0d1426}
.hint{display:none;margin-top:10px;font-size:12.5px;color:var(--mute)}.hint.show{display:block}
.picks{display:grid;gap:22px;margin-top:clamp(40px,6vw,64px)}
.pick{position:relative;display:grid;grid-template-columns:300px 1fr;gap:clamp(20px,3vw,36px);overflow:hidden;
  background:linear-gradient(160deg,rgba(255,255,255,.06),rgba(255,255,255,.015) 40%),var(--glass);
  border:1px solid var(--line);border-radius:28px;padding:clamp(18px,3vw,32px);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.pick::before{content:"";position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--c),transparent)}
.pick-art{position:relative;align-self:start}
.pick-art .num{position:absolute;right:12px;top:6px;font-family:var(--serif);font-style:italic;font-size:54px;line-height:1;color:transparent;-webkit-text-stroke:1.2px rgba(255,197,49,.8)}
.badge{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#14110a;background:var(--amber);border-radius:999px;padding:5px 11px}
.pick h2{margin-top:12px;font-weight:800;font-size:clamp(24px,2.8vw,32px);letter-spacing:-.025em;line-height:1.1}
.pick h2 a{color:var(--ink);text-decoration:none}.pick h2 a:hover{color:var(--amber)}
.sum{margin-top:10px;font-family:var(--serif);font-style:italic;font-size:clamp(19px,1.8vw,23px);line-height:1.35;color:#e8e1d2}
.pick h3,.fit h3{font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--mute);margin-bottom:8px}
.specs{margin-top:20px;padding:16px 18px;border-radius:16px;background:rgba(0,0,0,.22);border:1px solid var(--line2)}
.specs ul{list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:6px 22px}
.specs li{display:flex;gap:10px;font-size:15px;line-height:1.45;color:var(--ink2)}
.specs li::before{content:"";flex:none;width:12px;height:2px;margin-top:10px;background:var(--amber)}
.fit{margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:12px}
.fit>div{padding:16px 18px;border-radius:16px;border:1px solid var(--line);background:var(--glass2)}
.fit p{font-size:15px;line-height:1.5;color:var(--ink2)}
.good h3{color:var(--lime)}.watch h3{color:var(--peach)}
.good{box-shadow:inset 3px 0 0 var(--lime)}.watch{box-shadow:inset 3px 0 0 var(--peach)}
.pick .cta-row{margin-top:22px}
.checks{list-style:none;display:grid;gap:12px}
.checks li{display:flex;gap:14px;font-size:16px;line-height:1.55;color:var(--ink2)}
.checks li::before{content:"";flex:none;width:22px;height:22px;margin-top:2px;border-radius:50%;background:rgba(155,225,93,.15) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%239be15d' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 12.5l4.5 4.5L19 7.5'/%3E%3C/svg%3E") center/13px no-repeat;border:1px solid rgba(155,225,93,.45)}
.minis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.mini,.tile{position:relative;overflow:hidden;display:flex;flex-direction:column;gap:10px;text-decoration:none;color:var(--ink);padding:22px;border-radius:22px;border:1px solid var(--line);
  background:linear-gradient(160deg,color-mix(in srgb,var(--c) 9%,transparent),transparent 50%),var(--glass);transition:transform .3s var(--ease),border-color .3s}
.mini:hover,.tile:hover{transform:translateY(-4px);border-color:color-mix(in srgb,var(--c) 55%,transparent)}
.mini strong{font-size:17px;line-height:1.3;font-weight:700}
.mini strong em,.tile h3 em{color:#e8e1d2;font-size:1.05em;margin-top:2px}
.tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.tile{padding:26px 26px 22px;min-height:230px}
.tile h3{font-size:clamp(20px,2vw,24px);line-height:1.15;letter-spacing:-.02em;font-weight:800}
.tile p{font-size:15px;line-height:1.55;color:var(--mute);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.tn{position:absolute;right:22px;top:14px;font-family:var(--serif);font-style:italic;font-size:50px;line-height:1;color:transparent;-webkit-text-stroke:1px rgba(255,255,255,.18);transition:-webkit-text-stroke-color .3s}
.tile:hover .tn{-webkit-text-stroke-color:var(--c)}
.jump{display:flex;flex-wrap:wrap;gap:8px;margin-top:26px}
.jump a{display:inline-flex;align-items:center;gap:7px;font-size:13.5px;font-weight:600;color:var(--ink2);text-decoration:none;padding:9px 14px;border-radius:999px;border:1px solid var(--line);background:var(--glass2)}
.jump a .i{color:var(--c)}.jump a:hover{border-color:var(--c)}

/* product page */
.pp{padding-top:clamp(26px,4vw,48px)}
.pp-grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:clamp(22px,4vw,52px);align-items:start}
.pp-art{position:sticky;top:120px}
.pp-art .art{border-radius:28px;box-shadow:0 40px 80px -40px color-mix(in srgb,var(--c) 60%,transparent)}
.pp-h{margin-top:14px;font-size:clamp(32px,4.4vw,54px)}
.pp-buy{margin:26px 0 8px;padding:18px;border-radius:20px;border:1px solid color-mix(in srgb,var(--c) 35%,transparent);background:color-mix(in srgb,var(--c) 6%,transparent)}
.pp-buy .btn{width:100%}
.spec-list{list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 26px}
.spec-list li{display:flex;gap:10px;align-items:flex-start;font-size:15.5px;color:var(--ink2);padding:10px 0;border-bottom:1px solid var(--line2)}
.spec-list .i{color:var(--lime);margin-top:3px}
.guide-link{display:grid;grid-template-columns:1fr auto;gap:22px;align-items:center;background:linear-gradient(120deg,color-mix(in srgb,var(--c) 10%,transparent),transparent 60%),var(--glass)}
.guide-link h2{font-size:clamp(22px,2.4vw,30px);font-weight:800;letter-spacing:-.02em;line-height:1.1;margin:6px 0 8px}
.guide-link p{color:var(--mute);font-size:15px;max-width:62ch;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.frame{position:relative;aspect-ratio:16/9;border-radius:18px;overflow:hidden;border:1px solid var(--line)}
.frame iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.buybar{position:fixed;left:0;right:0;bottom:0;z-index:50;padding:10px var(--pad) calc(10px + env(safe-area-inset-bottom));background:rgba(9,14,27,.94);border-top:1px solid color-mix(in srgb,var(--c) 40%,transparent);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);transform:translateY(110%);transition:transform .35s var(--ease)}
.buybar.on{transform:none}
.bb-in{max-width:var(--max);margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:14px}
.bb-name{font-weight:700;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* prose */
.prose p{font-size:17px;line-height:1.7;color:var(--ink2);max-width:68ch}
.prose p+p{margin-top:14px}

/* footer */
.foot{margin-top:90px;border-top:1px solid var(--line);background:linear-gradient(transparent,rgba(0,0,0,.4));padding:0 0 calc(40px + env(safe-area-inset-bottom))}
.foot-cta{max-width:var(--max);margin:-1px auto 0;padding:clamp(30px,5vw,54px) var(--pad);display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:20px;border-bottom:1px solid var(--line)}
.foot-cta h2{font-size:clamp(28px,3.6vw,44px);font-weight:800;letter-spacing:-.03em;line-height:1.05;margin-top:6px}
.foot-cta .k{color:var(--lime)}
.foot-cta-btns{display:flex;flex-wrap:wrap;gap:10px}
.foot-in{max-width:var(--max);margin:0 auto;padding:44px var(--pad) 0;display:grid;grid-template-columns:1fr 2.4fr;gap:40px}
.foot .tag{margin:14px 0 18px;font-size:20px;color:#e8e1d2;font-family:var(--serif);font-style:italic}
.foot .tag em{display:inline}
.foot-cols{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:26px 20px}
.foot-cols h4{font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--c,var(--amber));margin-bottom:10px}
.foot-cols a{display:block;color:var(--mute);text-decoration:none;font-size:14px;padding:4px 0}
.foot-cols a:hover{color:var(--ink)}
.fine{max-width:var(--max);margin:36px auto 0;padding:0 var(--pad);font-size:12.5px;line-height:1.6;color:rgba(169,178,198,.8)}

/* reveal */
.js .rv{opacity:0;transform:translateY(22px);transition:opacity .7s var(--ease),transform .7s var(--ease)}
.js .rv.in{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.js .rv{opacity:1;transform:none;transition:none}
  .dot,.big-vial,.bv-bubble,.float,.art-ring,.promo{animation:none}}

@media (max-width:1060px){.cards{grid-template-columns:repeat(3,minmax(0,1fr))}.foot-cols{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:900px){
  .links,.search-btn span{display:none}
  .bar-r{margin-left:auto}.menu{display:block}
  .home-hero{grid-template-columns:1fr}
  .hh-art{max-width:400px;aspect-ratio:5/4}
  .cats{grid-template-columns:repeat(2,minmax(0,1fr))}
  .cards{grid-template-columns:repeat(2,minmax(0,1fr))}
  .spot,.pp-grid,.guide-link{grid-template-columns:1fr}
  .pp-art{position:static}
  .pp-art .art.xl{aspect-ratio:16/7}
  .pp-art .art.xl .art-i{width:26%;height:auto;aspect-ratio:1}
  .pp-art .art.xl .art-ring{width:36%}
  .pick{grid-template-columns:1fr}
  .pick-art{max-width:360px}
  .how-grid,.minis{grid-template-columns:1fr}
  .foot-in{grid-template-columns:1fr}
  .hint{display:block}
}
@media (max-width:620px){
  .promo{font-size:12px;gap:7px}.promo .sep,.promo-go{display:none}
  .brand{letter-spacing:.16em;font-size:12px;gap:10px}
  .tiles,.gls{grid-template-columns:1fr}
  .cats{gap:10px}.cat{padding:16px}.cat p{display:none}.cat h3{font-size:16px}.cat-i{width:40px;height:40px;margin-bottom:2px}
  .hh-art{aspect-ratio:4/3;max-width:360px}
  .cards{gap:12px}
  .card-art{padding:8px 8px 0}.card-body{padding:12px}
  .card h3{font-size:15px}.card-badge{font-size:15px}.card-sum{display:none}
  .card-cta{flex-direction:column;align-items:stretch}.card-cta .btn{width:100%}.card-cta .lnk{justify-content:center}
  .fit,.spec-list{grid-template-columns:1fr}
  .pick-art{max-width:none}.pick-art .art{aspect-ratio:16/8}.pick-art .art .art-i{width:28%;height:auto;aspect-ratio:1}.pick-art .art-ring{width:40%}
  .follow-in,.books-teaser,.book{grid-template-columns:1fr}
  .follow-art{display:none}
  .bt-cover{margin:0 auto}
  .foot-cols{grid-template-columns:repeat(2,minmax(0,1fr))}
  .home-hero .btn.lg,.foot-cta-btns .btn{width:100%}
  .float{font-size:12px}.float .i{width:30px;height:30px}
  .tile{min-height:0}
}

/* ── editorial pass: open layout, fewer boxes, soft bands ── */
body::after{display:none}
.glow{background:radial-gradient(1200px 700px at 90% -10%,rgba(255,197,49,.10),transparent 60%),radial-gradient(1000px 700px at -15% 40%,rgba(155,225,93,.06),transparent 60%)}
.meta{font-size:13px;font-weight:500;letter-spacing:0;text-transform:none;color:var(--mute)}
.meta .dot{display:none}
.sect-head .k{display:none}
.sect-head h2 em,.sec em,.h2 em:not(.keep){font-family:inherit;font-style:inherit;font-weight:inherit;color:inherit;letter-spacing:inherit}
.h2{font-weight:800;font-size:clamp(26px,3.2vw,38px);letter-spacing:-.025em;line-height:1.08;margin-bottom:22px}
.h2.big{font-size:clamp(34px,5vw,60px);line-height:1.02}
.h2.big em{display:block;font-family:var(--serif);font-style:italic;font-weight:400;color:var(--c)}
.sect-head{align-items:baseline;justify-content:space-between}
.sect-head .h2,.sect-head h2{margin-bottom:0}
.note{font-family:var(--serif);font-style:italic;font-size:20px;color:var(--c,var(--amber));margin-bottom:4px}
.quiet{margin-top:22px;font-size:13.5px;color:var(--mute)}
.lnk.big{font-size:16px}
.band-p{color:#c9cfdc;font-size:clamp(16px,1.4vw,18px);max-width:56ch;margin-bottom:20px}
.sect{margin-top:clamp(64px,9vw,120px)}

/* soft full-width color band that fades in and out instead of a box */
.band{position:relative;isolation:isolate}
.band::before{content:"";position:absolute;z-index:-1;top:-90px;bottom:-90px;left:50%;width:100vw;transform:translateX(-50%);
  background:radial-gradient(60% 70% at 25% 50%,color-mix(in srgb,var(--c) 16%,transparent),transparent 70%),radial-gradient(50% 60% at 85% 40%,color-mix(in srgb,var(--c) 8%,transparent),transparent 70%);
  -webkit-mask-image:linear-gradient(transparent,#000 30%,#000 70%,transparent);mask-image:linear-gradient(transparent,#000 30%,#000 70%,transparent);pointer-events:none}

/* home hero */
.home-hero{padding-top:clamp(40px,7vw,96px)}
.home-hero{grid-template-columns:1.35fr .65fr}
.home-hero h1{font-size:clamp(46px,6.4vw,86px)}
.home-hero .cta-row{margin-top:32px;gap:22px}
.home-hero .lede{font-size:clamp(18px,1.7vw,21px)}
.hh-art{aspect-ratio:auto;height:clamp(220px,30vw,380px);max-width:none}
.big-vial{left:2%;right:2%;top:32%;height:34%}

/* categories as a flowing line of links */
.catflow{display:flex;flex-wrap:wrap;gap:6px 34px;align-items:baseline}
.catflow a{display:inline-flex;align-items:center;gap:12px;text-decoration:none;color:var(--ink);font-weight:700;font-size:clamp(22px,2.8vw,34px);letter-spacing:-.02em;line-height:1.5;
  background:linear-gradient(var(--c),var(--c)) 0 100%/0 2px no-repeat;transition:background-size .35s var(--ease),color .2s}
.catflow a:hover{background-size:100% 2px;color:var(--c)}
.catflow .cf{width:.9em;height:.9em;color:var(--c);stroke-width:1.8}
.catflow sup{font-size:.42em;font-weight:600;color:var(--mute);letter-spacing:0;align-self:flex-start;margin-top:.5em}

/* product cards without the box */
.cards{gap:clamp(18px,2.4vw,32px) clamp(14px,2vw,26px)}
.card{border:0;background:none;border-radius:0;overflow:visible}
.card:hover{transform:none}
.card-art{padding:0}
.card .art{transition:transform .45s var(--ease),box-shadow .45s var(--ease)}
.card:hover .art{transform:translateY(-4px);box-shadow:0 26px 50px -28px color-mix(in srgb,var(--c) 70%,transparent)}
.card-body{padding:14px 2px 0;gap:4px}
.card-body .k{letter-spacing:.06em;text-transform:none;font-weight:600;font-size:12.5px}
.card-cta{padding-top:12px;justify-content:flex-start;gap:16px}
.art{border:0;border-radius:20px}

/* spotlight */
.spot{border:0;background:none;padding:0;border-radius:0;gap:clamp(24px,5vw,64px)}
.spot .art{box-shadow:0 40px 80px -40px color-mix(in srgb,var(--c) 70%,transparent)}
.spot h2{margin-top:2px}
.spot .cta-row{gap:22px}

/* how picks get made: three short columns, no cards */
.how-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:clamp(20px,4vw,48px);margin-bottom:22px}
.how-i{padding:18px 0 0;border:0;border-top:2px solid rgba(255,255,255,.14);border-radius:0;background:none}
.how-i:first-child{border-top-color:var(--lime)}
.how-i h3{font-size:19px;font-weight:700;margin-bottom:6px}
.how-i p{font-size:15.5px;color:var(--mute)}

/* follow + books */
.follow .socs{gap:10px}
.books-teaser,.book{border:0;background:none;padding:0;border-radius:0}
.books-teaser .note,.book .note{color:var(--lime)}

/* guide list: plain rows */
.gls{gap:0 40px}
.gl{border:0;border-bottom:1px solid var(--line2);border-radius:0;background:none;padding:16px 2px;gap:12px}
.gl:hover{background:none}
.gl b{font-size:16.5px;font-weight:600;transition:color .2s}
.gl:hover b{color:var(--c)}
.gl small{margin-left:auto;white-space:nowrap}
.gl>.i{margin-left:0;transition:transform .25s,color .2s}
.gl:hover>.i{transform:translateX(3px);color:var(--c)}

/* inner pages: open blocks */
.block{background:none;border:0;padding:0;border-radius:0;backdrop-filter:none;-webkit-backdrop-filter:none}
.picks{gap:0;margin-top:clamp(36px,5vw,56px)}
.pick{background:none;border:0;border-radius:0;padding:clamp(34px,5vw,60px) 0;border-top:1px solid var(--line);backdrop-filter:none;-webkit-backdrop-filter:none;overflow:visible}
.pick::before{display:none}
.pick-art .num{-webkit-text-stroke:0;color:rgba(255,255,255,.85);font-size:44px;right:16px;top:10px;text-shadow:0 2px 20px rgba(0,0,0,.5)}
.specs{background:none;border:0;padding:0;margin-top:24px}
.fit{gap:24px;margin-top:22px}
.fit>div{background:none;border:0;border-radius:0;padding:2px 0 2px 16px}
.qps{gap:0 32px}
.qp{border:0;border-bottom:1px solid var(--line2);border-radius:0;background:none;padding:12px 0}
.qp:hover{transform:none;background:none}
.qp:hover span:last-child{color:var(--amber)}
.mini,.tile{background:none;border:0;border-top:2px solid color-mix(in srgb,var(--c) 70%,transparent);border-radius:0;padding:18px 0 0}
.mini:hover,.tile:hover{transform:none}
.mini:hover strong,.tile:hover h3{color:var(--c)}
.tile{min-height:0}
.tn{display:none}
.tiles{gap:34px 40px}
.minis{gap:28px}
.guide-link{border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:28px 0;background:none}
.pp-buy{border:0;background:none;padding:0}
.pp-art .art{border-radius:28px}
.spec-list li{border-bottom-color:var(--line2)}
.cat-pill{border:0;padding:0;background:none;letter-spacing:.06em;text-transform:none;font-size:14px;font-weight:600}
.jump a{border:0;background:none;padding:6px 0;margin-right:16px;font-size:15px}
.jump a:hover{color:var(--c)}
.finder{border-color:var(--line2)}
.foot-cta .k{display:none}
.foot-cta h2 em{font-family:inherit;font-style:inherit;font-weight:inherit;color:inherit}

@media (max-width:900px){
  .home-hero{grid-template-columns:1fr;gap:10px}
  .hh-art{height:200px}
  .how-row{grid-template-columns:1fr}
}
@media (max-width:620px){
  .catflow{gap:2px 22px}
  .catflow a{font-size:22px}
  .gls{grid-template-columns:1fr}
  .home-hero .cta-row{flex-direction:column;align-items:stretch}
  .home-hero .lnk.big{justify-content:center}
  .card-cta{flex-direction:column;align-items:stretch;gap:10px}
  .card-cta .btn{width:100%}
  .card-cta .lnk{justify-content:center}
  .hh-art{height:150px}
  .pick{padding:30px 0}
}
"""


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    write("style.css", CSS.strip() + "\n")
    write(".nojekyll", "")
    write("CNAME", "levelpicks.com\n")  # keeps the custom domain after each rebuild
    for d in ("brand", "media"):
        if os.path.isdir(os.path.join(ROOT, d)):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(OUT, d))
    home()
    picks_page()
    guides_index()
    for g in S["guides"]:
        guide_page(g)
    for p in PRODUCTS:
        product_page(p)
    books_page()
    about_page()
    simple("disclosure", "Affiliate disclosure", [
        DISCLOSURE_LONG,
        "Level Picks is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. It may also join other retailers' affiliate programs.",
        "Commissions don't change what you pay, and they don't decide which products make a list.",
    ])
    simple("privacy", "Privacy policy", [
        "This site uses Google Analytics (through a Google tag) to count visits, see which pages are read and measure clicks out to retailers like Amazon. Google Analytics sets cookies and receives your IP address and basic device and browser details. We don't run ads, we don't sell data, and we don't collect names, emails or other personal information.",
        "You can block Google Analytics with your browser's privacy settings or Google's opt-out add-on (tools.google.com/dlpage/gaoptout). See Google's privacy policy for how it handles data.",
        "The site is hosted on GitHub Pages, which may log basic technical data such as IP addresses for security. Fonts load from Google Fonts, which receives your IP address to serve them. Product videos, where a page has one, load from YouTube's privacy-enhanced mode. See GitHub's, Google's and YouTube's privacy statements for details.",
        "When you click a link to Amazon or another retailer, that site may set cookies to credit the referral. Their own privacy policies apply once you leave this site.",
    ])
    not_found()
    urls = ["", "picks/", "guides/", "books/", "about/", "disclosure/", "privacy/"] + \
           [f"guides/{g['slug']}/" for g in S["guides"]] + [f"p/{p['_slug']}/" for p in PRODUCTS]
    sm = "".join(f"<url><loc>{S['base_url']}/{u}</loc></url>" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {S['base_url']}/sitemap.xml\n")
    print("built", sum(len(fs) for _, _, fs in os.walk(OUT)), "files,", len(PRODUCTS), "product pages")


if __name__ == "__main__":
    main()
