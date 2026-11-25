# Shop Floor Picks

Affiliate buying-guide site for welding and fab-shop gear.
Live: https://levelpicks.com

## How it works
- `site.json` holds everything: site name, Amazon tag, guides and products.
- `python3 build.py` turns it into the website in `docs/`.
- GitHub Pages serves `docs/` from the `main` branch.

## Common changes
- **Add a product:** copy one product block inside a guide's `"products"` list and edit it.
  Use `"url": "https://www.amazon.com/dp/<ASIN>?tag=wesellfab01-20"` for an exact listing,
  or `"search"` for an Amazon search. Each product gets its own page at `/p/<name>/`.
  Optional fields: `"icon"` (helmet, grinder, plasma, drill, goggles…; see ICONS in build.py),
  `"featured": 1` (shows on the homepage, lower = first), `"hands_on": true` (adds the
  "Filmed hands-on" stamp once you've filmed it), `"video"` (a YouTube or TikTok link),
  `"image": "media/<file>.jpg"` (your own photo, saved in a `media/` folder).
- **Add a guide:** copy a whole guide block in `"guides"`, give it a new `"slug"`, and add
  that slug to one of the `"categories"`.
- **Black Friday bar:** `"promo"` in `site.json`. It counts down and hides itself after `"ends"`.
- **Books:** `"books"` in `site.json`. Set `"status": "available"` and a `"url"` when one is for sale.

## Publish
```
cd "<this folder>"
python3 build.py
git add -A && git commit -m "Update guides" && git push
```

## Rules to keep
- Keep the Amazon disclosure on every page (built in).
- Don't show prices or copy Amazon product photos onto the site.
- Use your own photos, or none.
