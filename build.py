#!/usr/bin/env python3
"""Builds the Level Picks static site from site.json into ./docs.

Add a product: append an object to a guide's "products" list in site.json.
Add a guide:  append an object to "guides".
Set the Amazon Associates tag once in "amazon_tag" (e.g. "shopfloorpick-20").
Then run:  python3 build.py
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


def amazon_link(query):
    q = {"k": query}
    if S["amazon_tag"]:
        q["tag"] = S["amazon_tag"]
    return "https://www.amazon.com/s?" + urllib.parse.urlencode(q)


def product_link(p):
    return p.get("url") or amazon_link(p["search"])


def page(title, desc, body, depth):
    up = "../" * depth
    nav = f'<a href="{up}#guides">All guides</a><a href="{up}about/">About</a>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="{up}"><span class="vial"><i></i></span>{e(S["name"])}</a>
  <nav>{nav}</nav>
</div></header>
<div class="note"><div class="wrap">{e(DISCLOSURE)}</div></div>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
  <p><a href="{up}about/">About</a> · <a href="{up}disclosure/">Affiliate disclosure</a> · <a href="{up}privacy/">Privacy</a></p>
  <p class="small">{e(DISCLOSURE_LONG)} Product details come from manufacturer and retailer specs; prices change, so check the current listing before you buy. Updated {e(S["updated"])}.</p>
</div></footer>
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
    return f'<div class="tablewrap"><table class="compare"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def guide_page(g):
    cards = []
    for i, p in enumerate(g["products"], 1):
        specs = "".join(f"<li>{e(s)}</li>" for s in p["specs"])
        cards.append(f"""
<article class="card" id="pick-{i}">
  <div class="badge">{e(p["badge"])}</div>
  <h2>{i}. {e(p["name"])}</h2>
  <p>{e(p["summary"])}</p>
  <ul class="specs">{specs}</ul>
  <p><strong>Good for:</strong> {e(p["good_for"])}</p>
  <p><strong>Watch for:</strong> {e(p["watch_for"])}</p>
  <a class="btn" href="{e(product_link(p))}" target="_blank" rel="sponsored nofollow noopener">{e(p.get("cta", "Check price on Amazon"))}</a>
</article>""")
    quick = "".join(f'<li><a href="#pick-{i}">{e(p["badge"])}: {e(p["name"])}</a></li>'
                    for i, p in enumerate(g["products"], 1))
    look = "".join(f"<li>{e(x)}</li>" for x in g["what_to_look_for"])
    body = f"""
<article class="guide">
  <h1>{e(g["title"])}</h1>
  <p class="lede">{e(g["intro"])}</p>
  <div class="quick"><h3>Quick picks</h3><ol>{quick}</ol></div>
  {compare_table(g)}
  {''.join(cards)}
  <section class="look"><h2>What to look for</h2><ul>{look}</ul></section>
</article>"""
    write(f"guides/{g['slug']}/index.html", page(f'{g["title"]} | {S["name"]}', g["intro"], body, 2))


def home():
    tiles = "".join(f"""
<a class="tile" href="guides/{g['slug']}/">
  <h2>{e(g["title"])}</h2>
  <p>{e(g["intro"])}</p>
  <span>{len(g["products"])} pick{"s" if len(g["products"]) != 1 else ""} →</span>
</a>""" for g in S["guides"])
    body = f"""
<section class="hero">
  <h1>{e(S["name"])}</h1>
  <p class="lede">{e(S["tagline"])}</p>
</section>
<section class="tiles" id="guides">{tiles}</section>"""
    write("index.html", page(f'{S["name"]}: honest product picks and gift guides', S["tagline"], body, 0))


def simple(slug, title, paras):
    body = f'<article class="guide"><h1>{e(title)}</h1>' + "".join(f"<p>{e(x)}</p>" for x in paras) + "</article>"
    write(f"{slug}/index.html", page(f'{title} | {S["name"]}', paras[0], body, 1))


CSS = """
:root{--ink:#1d1f22;--muted:#5b616b;--line:#e3e5e8;--bg:#f6f6f4;--card:#fff;--accent:#b7791f;--dark:#0b1220}
*{box-sizing:border-box}
body{margin:0;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
.wrap{max-width:860px;margin:0 auto;padding:0 20px}
a{color:var(--accent)}
.top{background:var(--dark);color:#fff}
.top .wrap{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 20px;padding-top:14px;padding-bottom:14px}
.brand{color:#fff;font-weight:800;font-size:20px;text-decoration:none;letter-spacing:1.5px;text-transform:uppercase;display:flex;align-items:center;gap:10px}
.vial{display:inline-block;width:38px;height:16px;border:3px solid #ffc531;border-radius:10px;background:rgba(155,225,93,.25);position:relative}
.vial i{position:absolute;left:11px;top:2px;width:10px;height:6px;border-radius:50%;background:#fff}
.top nav a{font-weight:600}
.top nav a{color:#d6d8db;text-decoration:none;margin-left:18px;font-size:15px}
.top nav a:first-child{margin-left:0}
.top nav a:hover{color:#fff}
.note{background:#fff4ec;border-bottom:1px solid #f3d6c3;font-size:13px;color:#7a4a2c}
.note .wrap{padding-top:8px;padding-bottom:8px}
main{padding-top:28px;padding-bottom:40px}
h1{font-size:34px;line-height:1.2;margin:0 0 12px}
h2{font-size:23px;line-height:1.3;margin:0 0 10px}
.lede{font-size:18px;color:var(--muted);margin:0 0 22px}
.hero{padding:18px 0 8px}
.tiles{display:grid;gap:16px}
.tile{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px 22px;text-decoration:none;color:var(--ink)}
.tile:hover{border-color:var(--accent)}
.tile p{color:var(--muted);margin:0 0 8px}
.tile span{color:var(--accent);font-weight:700}
.quick{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;padding:12px 20px;margin:0 0 24px}
.quick h3{margin:4px 0 4px;font-size:15px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted)}
.quick ol{margin:0;padding-left:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:22px 24px;margin:0 0 20px}
.badge{display:inline-block;background:#ffc531;color:#0b1220;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;border-radius:4px;padding:3px 8px;margin-bottom:10px}
.specs{background:var(--bg);border-radius:8px;padding:12px 16px 12px 34px;margin:12px 0}
.specs li{margin:2px 0}
.btn{display:inline-block;background:var(--dark);color:#fff;text-decoration:none;font-weight:700;border-radius:8px;padding:11px 18px;margin-top:4px}
.btn:hover{background:var(--accent)}
.tablewrap{overflow-x:auto;margin:0 0 24px}
.compare{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:8px;font-size:15px}
.compare th,.compare td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
.compare th{background:var(--dark);color:#fff;font-weight:600}
.compare tr:last-child td{border-bottom:0}
.look{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px 24px}
.look li{margin:6px 0}
footer{border-top:1px solid var(--line);background:#fff;color:var(--muted);font-size:14px}
footer .wrap{padding-top:18px;padding-bottom:22px}
.small{font-size:13px}
@media (max-width:560px){h1{font-size:28px}.top nav a{margin-left:12px}}
"""


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    write("style.css", CSS.strip() + "\n")
    write(".nojekyll", "")
    home()
    # 3D storefront becomes the home page; the plain guide list moves to /guides/
    sf = os.path.join(ROOT, "storefront.html")
    if os.path.exists(sf):
        os.makedirs(os.path.join(OUT, "guides"), exist_ok=True)
        shutil.move(os.path.join(OUT, "index.html"), os.path.join(OUT, "guides", "index.html"))
        content = open(os.path.join(OUT, "guides", "index.html")).read().replace('href="guides/', 'href="./').replace('href="style.css"', 'href="../style.css"').replace('href="about/', 'href="../about/').replace('href="disclosure/', 'href="../disclosure/').replace('href="privacy/', 'href="../privacy/').replace('href="#guides"', 'href="./"').replace('class="brand" href=""', 'class="brand" href="../"')
        open(os.path.join(OUT, "guides", "index.html"), "w").write(content)
        shutil.copy(sf, os.path.join(OUT, "index.html"))
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
        "The site is hosted on GitHub Pages, which may log basic technical data such as IP addresses for security. See GitHub's privacy statement for details.",
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
