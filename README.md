# Shop Floor Picks

Affiliate buying-guide site for welding and fab-shop gear.
Live: https://lanesprecisionmetalservices.github.io/shopfloor-picks/

## How it works
- `site.json` holds everything: site name, Amazon tag, guides and products.
- `python3 build.py` turns it into the website in `docs/`.
- GitHub Pages serves `docs/` from the `main` branch.

## Common changes
- **Add your Amazon Associates tag:** set `"amazon_tag": "yourtag-20"` in `site.json`, rebuild, push.
- **Add a product:** copy one product block inside a guide's `"products"` list and edit it.
  By default the button links to an Amazon search for `"search"`. To link one exact
  listing instead, add `"url": "https://amzn.to/..."` (a SiteStripe link) to that product.
- **Add a guide:** copy a whole guide block in `"guides"` and give it a new `"slug"`.

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
