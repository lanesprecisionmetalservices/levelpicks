#!/usr/bin/env python3
"""Builds the Level Picks static site from site.json into ./docs.

Add a product: append an object to a guide's "products" list in site.json.
Add a guide:  append an object to "guides" (give it a short "short" label for the guide bar).
Set the Amazon Associates tag once in "amazon_tag".
Then run:  python3 build.py

Layout:
  /                 3D storefront (storefront.html, copied as-is)
  /guides/          every guide, as cards
  /guides/<slug>/   one guide page
  /about/ /disclosure/ /privacy/
"""
import json, html, os, shutil, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
S = json.load(open(os.path.join(ROOT, "site.json")))
e = html.escape

DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."
DISCLOSURE_LONG = ("As an Amazon Associate I earn from qualifying purchases. Links to Amazon on this site "
                   "are affiliate links. If you buy through one, the site may earn a commission. "
                   "The price you pay is the same.")

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800'
         '&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">')


def amazon_link(query):
    q = {"k": query}
    if S["amazon_tag"]:
        q["tag"] = S["amazon_tag"]
    return "https://www.amazon.com/s?" + urllib.parse.urlencode(q)


def product_link(p):
    return p.get("url") or amazon_link(p["search"])


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def styled_title(t):
    """'Main part: the rest' -> main part, then the rest in the italic serif accent."""
    if ":" in t:
        a, b = t.split(":", 1)
        return f'{e(a.strip())}<em>{e(b.strip())}</em>'
    return e(t)


def guide_rail(up, current=None):
    chips = [f'<a href="{up}guides/"{" aria-current=page" if current == "__all" else ""}>All guides</a>']
    for g in S["guides"]:
        cur = ' aria-current="page"' if g["slug"] == current else ""
        chips.append(f'<a href="{up}guides/{g["slug"]}/"{cur}>{e(g.get("short") or g["title"])}</a>')
    return f'<nav class="rail" aria-label="Guides"><div class="rail-in">{"".join(chips)}</div></nav>'


def page(title, desc, body, depth, current=None, canonical=""):
    up = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#070b16">
<link rel="canonical" href="{e(S['base_url'])}/{canonical}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
{FONTS}
<link rel="stylesheet" href="{up}style.css">
<script>document.documentElement.classList.add("js")</script>
</head>
<body>
<div class="glow" aria-hidden="true"></div>
<header class="top">
  <div class="bar">
    <a class="brand" href="{up}" aria-label="{e(S['name'])} storefront"><span class="vial"><i></i></span>{e(S["name"])}</a>
    <nav class="links">
      <a href="{up}">Storefront</a>
      <a href="{up}guides/"{' aria-current="page"' if current == "__all" else ""}>Guides</a>
      <a href="{up}about/">About</a>
    </nav>
  </div>
  {guide_rail(up, current)}
  <div class="progress" aria-hidden="true"><b></b></div>
</header>
<main>
{body}
</main>
<footer class="foot">
  <div class="foot-in">
    <div>
      <a class="brand" href="{up}"><span class="vial"><i></i></span>{e(S["name"])}</a>
      <p class="tag">{e(S["tagline"])}</p>
    </div>
    <nav><a href="{up}guides/">All guides</a><a href="{up}about/">About</a><a href="{up}disclosure/">Affiliate disclosure</a><a href="{up}privacy/">Privacy</a></nav>
  </div>
  <p class="fine">{e(DISCLOSURE_LONG)} Product details come from manufacturer and retailer specs; prices change, so check the current listing before you buy. Updated {e(S["updated"])}.</p>
</footer>
<script>{JS}</script>
</body>
</html>
"""


def write(rel, content):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(content)


def compare_table(g):
    c = g.get("compare")
    if not c:
        return ""
    head = "".join(f"<th>{e(x)}</th>" for x in c["cols"])
    rows = "".join("<tr>" + "".join(f"<td>{e(x)}</td>" for x in r) + "</tr>" for r in c["rows"])
    return f"""
<section class="block rv" id="compare">
  <h2 class="sec">Side by side</h2>
  <div class="tablewrap"><table class="compare"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>
  <p class="hint">Swipe the table sideways on a phone.</p>
</section>"""


def more_guides(g):
    i = S["guides"].index(g)
    others = [S["guides"][(i + k) % len(S["guides"])] for k in range(1, 4) if len(S["guides"]) > k]
    cards = "".join(f"""
    <a class="mini rv" href="../{o['slug']}/">
      <span class="k">{e(o.get('short') or 'Guide')}</span>
      <strong>{styled_title(o['title'])}</strong>
      <span class="go">{plural(len(o['products']), 'pick')} <i>→</i></span>
    </a>""" for o in others)
    return f"""
<section class="block more">
  <div class="sec-row"><h2 class="sec">Keep <em>browsing</em></h2><a class="all" href="../">All guides →</a></div>
  <div class="minis">{cards}</div>
</section>"""


def guide_page(g):
    n = len(g["products"])
    cards = []
    for i, p in enumerate(g["products"], 1):
        specs = "".join(f"<li>{e(s)}</li>" for s in p["specs"])
        cards.append(f"""
<article class="pick rv" id="pick-{i}">
  <div class="num" aria-hidden="true">{i:02d}</div>
  <div class="pick-body">
    <span class="badge">{e(p["badge"])}</span>
    <h2>{e(p["name"])}</h2>
    <p class="sum">{e(p["summary"])}</p>
    <div class="specs"><h3>Key specs</h3><ul>{specs}</ul></div>
    <div class="fit">
      <div class="good"><h3>Good for</h3><p>{e(p["good_for"])}</p></div>
      <div class="watch"><h3>Watch for</h3><p>{e(p["watch_for"])}</p></div>
    </div>
    <div class="cta">
      <a class="btn" href="{e(product_link(p))}" target="_blank" rel="sponsored nofollow noopener">{e(p.get("cta", "Check price on Amazon"))} <span aria-hidden="true">↗</span></a>
      <span class="aff">Affiliate link · opens Amazon</span>
    </div>
  </div>
</article>""")
    quick = "".join(f"""
    <a class="qp" href="#pick-{i}"><span class="qn">{i:02d}</span><span><b>{e(p["badge"])}</b>{e(p["name"])}</span></a>"""
                    for i, p in enumerate(g["products"], 1))
    look = "".join(f"<li>{e(x)}</li>" for x in g["what_to_look_for"])
    body = f"""
<section class="hero">
  <div class="crumbs"><a href="../">Guides</a><span>/</span>{e(g.get("short") or g["title"])}</div>
  <div class="meta"><span class="dot"></span>{plural(n, "pick")} · Updated {e(S["updated"])}</div>
  <h1>{styled_title(g["title"])}</h1>
  <p class="lede">{e(g["intro"])}</p>
  <p class="disc">{e(DISCLOSURE)}</p>
  <div class="ruler" aria-hidden="true"><span></span></div>
</section>
<section class="block quick rv" aria-label="Quick picks">
  <h2 class="sec">Quick <em>picks</em></h2>
  <div class="qps">{quick}</div>
</section>
{compare_table(g)}
<section class="picks">{''.join(cards)}</section>
<section class="block look rv">
  <h2 class="sec">What to <em>look for</em></h2>
  <ul class="checks">{look}</ul>
</section>
{more_guides(g)}"""
    write(f"guides/{g['slug']}/index.html",
          page(f'{g["title"]} | {S["name"]}', g["intro"], body, 2, g["slug"], f"guides/{g['slug']}/"))


def guides_index():
    tiles = "".join(f"""
<a class="tile rv" href="{g['slug']}/">
  <span class="tn">{i:02d}</span>
  <span class="k">{e(g.get('short') or 'Guide')}</span>
  <h2>{styled_title(g["title"])}</h2>
  <p>{e(g["intro"])}</p>
  <span class="go">{plural(len(g["products"]), "pick")} <i>→</i></span>
</a>""" for i, g in enumerate(S["guides"], 1))
    body = f"""
<section class="hero">
  <div class="meta"><span class="dot"></span>{plural(len(S["guides"]), "guide")} · Updated {e(S["updated"])}</div>
  <h1>Every guide,<em>on one level shelf.</em></h1>
  <p class="lede">{e(S["tagline"])}</p>
  <p class="disc">{e(DISCLOSURE)}</p>
  <div class="ruler" aria-hidden="true"><span></span></div>
</section>
<section class="tiles">{tiles}</section>"""
    write("guides/index.html",
          page(f'All guides | {S["name"]}', S["tagline"], body, 1, "__all", "guides/"))


def simple(slug, title, paras):
    body = f"""
<section class="hero slim">
  <h1>{e(title)}</h1>
  <div class="ruler" aria-hidden="true"><span></span></div>
</section>
<article class="block prose rv">{''.join(f"<p>{e(x)}</p>" for x in paras)}</article>"""
    write(f"{slug}/index.html", page(f'{title} | {S["name"]}', paras[0], body, 1, None, f"{slug}/"))


JS = """
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
  var rail=document.querySelector('.rail-in'), cur=rail&&rail.querySelector('[aria-current]');
  if(cur&&cur.offsetLeft+cur.offsetWidth>rail.clientWidth-40){rail.scrollLeft=cur.offsetLeft-(rail.clientWidth-cur.offsetWidth)/2;}
  var els=document.querySelectorAll('.rv');
  if(!('IntersectionObserver' in window)){els.forEach(function(x){x.classList.add('in')});return;}
  var io=new IntersectionObserver(function(es){es.forEach(function(en){
    if(en.isIntersecting){en.target.classList.add('in');io.unobserve(en.target);}});},{rootMargin:'0px 0px -8% 0px'});
  els.forEach(function(x){io.observe(x)});
})();
"""

CSS = r"""
:root{--bg:#070b16;--bg2:#0b1222;--ink:#f4f1ea;--mute:#a9b2c6;--amber:#ffc531;--lime:#9be15d;--peach:#ffb38f;
--line:rgba(255,255,255,.12);--glass:rgba(16,22,40,.55);--glass2:rgba(255,255,255,.035);
--sans:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;--serif:"Instrument Serif",Georgia,serif;
--pad:clamp(18px,4vw,48px);--max:1080px}
*{box-sizing:border-box;margin:0;padding:0}
html{background:var(--bg);color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased;scroll-behavior:smooth;scroll-padding-top:150px}
body{min-height:100vh;font-size:16px;line-height:1.6;overflow-x:hidden;
  background:radial-gradient(1100px 650px at 85% -5%,rgba(255,197,49,.13),transparent 60%),
             radial-gradient(900px 600px at -10% 35%,rgba(155,225,93,.08),transparent 60%),
             radial-gradient(800px 600px at 110% 85%,rgba(120,140,255,.07),transparent 60%),var(--bg)}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.05;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);
  background-size:64px 64px;mask-image:radial-gradient(ellipse 80% 60% at 50% 0%,#000 30%,transparent 75%);-webkit-mask-image:radial-gradient(ellipse 80% 60% at 50% 0%,#000 30%,transparent 75%)}
main,.foot{position:relative;z-index:1}
::selection{background:var(--amber);color:#111}
a{color:var(--amber)}
:focus-visible{outline:2px solid var(--amber);outline-offset:3px;border-radius:6px}
em{font-family:var(--serif);font-style:italic;font-weight:400;color:var(--amber);letter-spacing:-.005em}

/* header + guide bar */
.top{position:sticky;top:0;z-index:30;background:rgba(7,11,22,.72);backdrop-filter:blur(16px) saturate(140%);-webkit-backdrop-filter:blur(16px) saturate(140%);border-bottom:1px solid transparent;transition:border-color .3s,background .3s}
.top.scrolled{border-bottom-color:var(--line);background:rgba(7,11,22,.86)}
.bar{max-width:var(--max);margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:calc(12px + env(safe-area-inset-top)) var(--pad) 10px}
.brand{display:inline-flex;align-items:center;gap:12px;color:var(--ink);text-decoration:none;font-weight:800;letter-spacing:.22em;font-size:13px;text-transform:uppercase}
.vial{width:42px;height:18px;border:2.5px solid var(--amber);border-radius:12px;background:rgba(155,225,93,.22);position:relative;flex:none;box-shadow:0 0 18px -6px rgba(255,197,49,.6)}
.vial::before,.vial::after{content:"";position:absolute;top:-2.5px;bottom:-2.5px;width:1.5px;background:var(--amber);opacity:.8}
.vial::before{left:12px}.vial::after{right:12px}
.vial i{position:absolute;top:3px;left:13px;width:12px;height:7px;border-radius:50%;background:#fff;box-shadow:0 0 8px rgba(255,255,255,.7);transition:transform .15s linear}
.links{display:flex;gap:2px}
.links a{color:var(--mute);text-decoration:none;font-size:13.5px;font-weight:500;padding:8px 13px;border-radius:999px;transition:color .2s,background .2s}
.links a:hover,.links a[aria-current]{color:var(--ink);background:rgba(255,255,255,.07)}
.rail{max-width:var(--max);margin:0 auto;padding:0 var(--pad) 12px;position:relative}
.rail::after{content:"";position:absolute;right:var(--pad);top:0;bottom:12px;width:40px;background:linear-gradient(90deg,transparent,rgba(7,11,22,.9));pointer-events:none}
.rail-in{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch;padding-right:40px}
.rail-in::-webkit-scrollbar{display:none}
.rail a{flex:none;font-size:13px;font-weight:500;color:#d4d9e6;text-decoration:none;padding:7px 14px;border-radius:999px;border:1px solid var(--line);background:var(--glass2);white-space:nowrap;transition:border-color .2s,background .2s,color .2s}
.rail a:hover{border-color:rgba(255,197,49,.5);color:var(--ink)}
.rail a[aria-current]{background:var(--amber);border-color:var(--amber);color:#14110a;font-weight:600}
.progress{position:absolute;left:0;right:0;bottom:-1px;height:2px}
.progress b{display:block;height:100%;background:linear-gradient(90deg,var(--lime),var(--amber));transform-origin:0 50%;transform:scaleX(0)}

/* layout */
main{max-width:var(--max);margin:0 auto;padding:0 var(--pad) 40px}
.hero{padding:clamp(40px,7vw,84px) 0 30px;max-width:860px}
.hero.slim{padding-bottom:20px}
.crumbs{font-size:13px;color:var(--mute);margin-bottom:18px;display:flex;gap:8px;align-items:center}
.crumbs a{color:var(--mute);text-decoration:none}.crumbs a:hover{color:var(--ink)}
.crumbs span{opacity:.5}
.meta{display:inline-flex;align-items:center;gap:9px;font-size:11.5px;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:var(--amber);margin-bottom:18px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--lime);box-shadow:0 0 12px var(--lime);animation:pulse 2.6s ease-in-out infinite}
@keyframes pulse{50%{opacity:.45}}
h1{font-weight:800;font-size:clamp(36px,6vw,68px);line-height:1.02;letter-spacing:-.035em;text-wrap:balance}
h1 em{display:block;margin-top:.12em;font-size:.86em;line-height:1.08}
.lede{margin-top:22px;max-width:60ch;font-size:clamp(17px,1.5vw,19.5px);line-height:1.6;color:#c9cfdc}
.disc{margin-top:16px;font-size:12.5px;color:var(--mute)}
.ruler{margin-top:34px;height:16px;position:relative;
  background:repeating-linear-gradient(90deg,rgba(255,255,255,.22) 0 1px,transparent 1px 12px) bottom/100% 6px no-repeat,
             repeating-linear-gradient(90deg,rgba(255,197,49,.55) 0 1px,transparent 1px 60px) bottom/100% 12px no-repeat;
  border-bottom:1px solid rgba(255,255,255,.18)}
.ruler span{position:absolute;left:50%;bottom:16px;width:58px;height:20px;transform:translateX(-50%);border:2px solid var(--amber);border-radius:12px;background:rgba(155,225,93,.18)}
.ruler span::after{content:"";position:absolute;top:4px;left:50%;width:16px;height:8px;margin-left:-8px;border-radius:50%;background:#fff;box-shadow:0 0 10px #fff;animation:float 5s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateX(-5px)}50%{transform:translateX(5px)}}

.block{margin-top:28px;background:var(--glass);border:1px solid var(--line);border-radius:24px;padding:clamp(20px,3vw,32px);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.sec{font-weight:800;font-size:clamp(22px,2.4vw,30px);letter-spacing:-.02em;line-height:1.1;margin-bottom:18px}
.sec-row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
.all{font-size:14px;font-weight:600;text-decoration:none}

/* quick picks */
.qps{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.qp{display:flex;gap:14px;align-items:center;text-decoration:none;color:var(--ink);padding:14px 16px;border-radius:16px;border:1px solid var(--line);background:var(--glass2);transition:transform .25s,border-color .25s,background .25s}
.qp:hover{transform:translateY(-2px);border-color:rgba(255,197,49,.45);background:rgba(255,197,49,.06)}
.qn{font-family:var(--serif);font-style:italic;font-size:30px;line-height:1;color:var(--amber);min-width:34px}
.qp b{display:block;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--lime);font-weight:600;margin-bottom:2px}
.qp span:last-child{font-size:15px;font-weight:600;line-height:1.3}

/* compare */
.tablewrap{overflow-x:auto;border-radius:16px;border:1px solid var(--line)}
.compare{width:100%;border-collapse:collapse;font-size:14.5px}
.compare th,.compare td{text-align:left;padding:12px 16px;white-space:nowrap}
.compare th{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--amber);font-weight:600;background:rgba(255,197,49,.06);border-bottom:1px solid var(--line)}
.compare td{border-bottom:1px solid rgba(255,255,255,.06);color:#d7dcea}
.compare tr:last-child td{border-bottom:0}
.compare tbody tr:hover td{background:rgba(255,255,255,.03)}
.compare td:first-child{font-weight:600;color:var(--ink);position:sticky;left:0;background:#0d1426}
.hint{display:none;margin-top:10px;font-size:12.5px;color:var(--mute)}

/* picks */
.picks{display:grid;gap:22px;margin-top:28px}
.pick{position:relative;display:grid;grid-template-columns:110px 1fr;gap:8px;overflow:hidden;
  background:linear-gradient(160deg,rgba(255,255,255,.06),rgba(255,255,255,.015) 40%),var(--glass);
  border:1px solid var(--line);border-radius:28px;padding:clamp(22px,3.2vw,38px);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.pick::before{content:"";position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,197,49,.7),transparent)}
.pick::after{content:"";position:absolute;width:340px;height:340px;right:-140px;top:-160px;border-radius:50%;background:radial-gradient(circle,rgba(255,197,49,.12),transparent 65%);pointer-events:none}
.num{font-family:var(--serif);font-style:italic;font-size:clamp(56px,7vw,92px);line-height:.85;color:transparent;-webkit-text-stroke:1.2px rgba(255,197,49,.75)}
.badge{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#14110a;background:var(--amber);border-radius:999px;padding:5px 11px}
.pick h2{margin-top:12px;font-weight:800;font-size:clamp(24px,2.8vw,34px);letter-spacing:-.025em;line-height:1.1}
.sum{margin-top:10px;font-family:var(--serif);font-style:italic;font-size:clamp(19px,1.8vw,23px);line-height:1.35;color:#e8e1d2}
.pick h3{font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--mute);margin-bottom:8px}
.specs{margin-top:20px;padding:16px 18px;border-radius:16px;background:rgba(0,0,0,.22);border:1px solid rgba(255,255,255,.06)}
.specs ul{list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:6px 22px}
.specs li{display:flex;gap:10px;font-size:15px;line-height:1.45;color:#d7dcea}
.specs li::before{content:"";flex:none;width:12px;height:2px;margin-top:10px;background:var(--amber)}
.fit{margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:12px}
.fit>div{padding:16px 18px;border-radius:16px;border:1px solid var(--line);background:var(--glass2)}
.fit p{font-size:15px;line-height:1.5;color:#d7dcea}
.good h3{color:var(--lime)}.watch h3{color:var(--peach)}
.good{box-shadow:inset 3px 0 0 var(--lime)}.watch{box-shadow:inset 3px 0 0 var(--peach)}
.cta{margin-top:22px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:10px;font:700 15px/1 var(--sans);text-decoration:none;color:#14110a;background:var(--amber);border-radius:999px;padding:15px 22px;box-shadow:0 12px 32px -12px rgba(255,197,49,.7);transition:transform .25s cubic-bezier(.2,.8,.2,1),background .25s}
.btn:hover{background:#ffd462;transform:translateY(-2px)}
.aff{font-size:12.5px;color:var(--mute)}

/* checklist */
.checks{list-style:none;display:grid;gap:12px}
.checks li{display:flex;gap:14px;font-size:16px;line-height:1.55;color:#d7dcea}
.checks li::before{content:"";flex:none;width:22px;height:22px;margin-top:2px;border-radius:50%;background:rgba(155,225,93,.15) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%239be15d' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 12.5l4.5 4.5L19 7.5'/%3E%3C/svg%3E") center/13px no-repeat;border:1px solid rgba(155,225,93,.45)}

/* more guides + index tiles */
.more{background:transparent;border:0;padding:0;backdrop-filter:none;-webkit-backdrop-filter:none;margin-top:56px}
.minis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.mini,.tile{display:flex;flex-direction:column;gap:10px;text-decoration:none;color:var(--ink);padding:22px;border-radius:22px;border:1px solid var(--line);background:var(--glass);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);transition:transform .3s cubic-bezier(.2,.8,.2,1),border-color .3s,background .3s;position:relative;overflow:hidden}
.mini:hover,.tile:hover{transform:translateY(-4px);border-color:rgba(255,197,49,.45);background:rgba(255,197,49,.05)}
.k{font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--lime)}
.mini strong{font-size:17px;line-height:1.3;font-weight:700}
.mini strong em,.tile h2 em{display:block;color:#e8e1d2;font-size:1.05em;margin-top:2px}
.go{margin-top:auto;font-size:13.5px;font-weight:600;color:var(--amber)}
.go i{font-style:normal;display:inline-block;transition:transform .25s}
.mini:hover .go i,.tile:hover .go i{transform:translateX(4px)}
.tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:8px}
.tile{padding:28px 28px 24px;min-height:260px}
.tile h2{font-size:clamp(21px,2vw,25px);line-height:1.15;letter-spacing:-.02em;font-weight:800}
.tile p{font-size:15px;line-height:1.55;color:var(--mute);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.tn{position:absolute;right:22px;top:14px;font-family:var(--serif);font-style:italic;font-size:54px;line-height:1;color:transparent;-webkit-text-stroke:1px rgba(255,255,255,.18);transition:-webkit-text-stroke-color .3s}
.tile:hover .tn{-webkit-text-stroke-color:rgba(255,197,49,.7)}

/* prose pages */
.prose p{font-size:17px;line-height:1.7;color:#d7dcea;max-width:68ch}
.prose p+p{margin-top:14px}

/* footer */
.foot{margin-top:70px;border-top:1px solid var(--line);background:linear-gradient(transparent,rgba(0,0,0,.35));padding:40px 0 calc(40px + env(safe-area-inset-bottom))}
.foot-in{max-width:var(--max);margin:0 auto;padding:0 var(--pad);display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:flex-start}
.foot .tag{margin-top:12px;max-width:44ch;font-family:var(--serif);font-style:italic;font-size:19px;line-height:1.35;color:#e8e1d2}
.foot nav{display:flex;flex-wrap:wrap;gap:6px 20px}
.foot nav a{color:var(--mute);text-decoration:none;font-size:14px}.foot nav a:hover{color:var(--ink)}
.fine{max-width:var(--max);margin:28px auto 0;padding:0 var(--pad);font-size:12.5px;line-height:1.6;color:rgba(169,178,198,.8)}

/* reveal */
.js .rv{opacity:0;transform:translateY(26px);transition:opacity .8s cubic-bezier(.2,.8,.2,1),transform .8s cubic-bezier(.2,.8,.2,1)}
.js .rv.in{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.js .rv{opacity:1;transform:none;transition:none}.dot,.ruler span::after{animation:none}}

@media (min-width:900px){.rail-in{flex-wrap:wrap;overflow:visible;padding-right:0;gap:6px}.rail a{font-size:12.5px;padding:6px 11px}.rail::after{display:none}}
@media (max-width:820px){
  .minis,.tiles{grid-template-columns:1fr}
  .pick{grid-template-columns:1fr}
  .num{font-size:64px;margin-bottom:-6px}
  .fit{grid-template-columns:1fr}
  .hint{display:block}
}
@media (max-width:520px){
  .links a:first-child{display:none}
  .brand{letter-spacing:.16em;font-size:12px}
  .tile{min-height:0}
  .btn{width:100%;justify-content:center}
}
"""


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    write("style.css", CSS.strip() + "\n")
    write(".nojekyll", "")
    write("CNAME", "levelpicks.com\n")  # keeps the custom domain after each rebuild
    guides_index()
    sf = os.path.join(ROOT, "storefront.html")
    if os.path.exists(sf):
        shutil.copy(sf, os.path.join(OUT, "index.html"))  # 3D storefront is the home page
    else:
        write("index.html", '<!DOCTYPE html><meta http-equiv="refresh" content="0;url=guides/">')
    for g in S["guides"]:
        guide_page(g)
    simple("about", "About Level Picks", [
        "Level Picks is run by a CNC plasma table operator and small fab-shop owner in Georgia.",
        "The guides cover gifts, car and garage gear, shop tools and deals worth knowing about. Picks are based on manufacturer specs and retailer listings, and each guide says what to watch out for. No brand pays to be on a list.",
        "Specs change when manufacturers update a model. The guides are checked and updated when that happens.",
    ])
    simple("disclosure", "Affiliate disclosure", [
        DISCLOSURE_LONG,
        "Level Picks is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. It may also join other retailers' affiliate programs.",
        "Commissions don't change what you pay, and they don't decide which products make a list.",
    ])
    simple("privacy", "Privacy policy", [
        "This site does not use analytics, ads or its own cookies, and it does not collect personal information.",
        "The site is hosted on GitHub Pages, which may log basic technical data such as IP addresses for security. Fonts load from Google Fonts, which receives your IP address to serve them. See GitHub's and Google's privacy statements for details.",
        "When you click a link to Amazon or another retailer, that site may set cookies to credit the referral. Their own privacy policies apply once you leave this site.",
    ])
    # sitemap
    urls = ["", "guides/", "about/", "disclosure/", "privacy/"] + [f"guides/{g['slug']}/" for g in S["guides"]]
    sm = "".join(f"<url><loc>{S['base_url']}/{u}</loc></url>" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {S['base_url']}/sitemap.xml\n")
    print("built", sum(len(fs) for _, _, fs in os.walk(OUT)), "files")


if __name__ == "__main__":
    main()
