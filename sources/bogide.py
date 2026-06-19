# Bog & Idé runs on Shopify. Their Pokémon catalogue lives in two public collections,
# each exposing a no-auth JSON endpoint with per-variant availability:
#   GET /collections/<handle>/products.json?limit=250
# A product is in stock if any of its variants is available. watch.py then keyword-
# filters to sealed product (booster/display/ETB) — safe here because the set is
# already scoped to Pokémon, so book titles never leak through.
import requests

BASE = "https://www.bog-ide.dk"
COLLECTIONS = ["pokemon", "pokemon-tcg"]
UA = "poke-watcher (personal restock notifier; github.com/LukasRathsach/poke-watcher)"


def _collection(handle):
    r = requests.get(
        f"{BASE}/collections/{handle}/products.json",
        params={"limit": 250},
        timeout=15,
        headers={"User-Agent": UA},
    )
    r.raise_for_status()
    return r.json().get("products", [])


def fetch(config):
    seen, items = set(), []
    for handle in COLLECTIONS:
        try:
            products = _collection(handle)
        except Exception as e:  # one failing collection must not kill the other
            print(f"[bogide] {handle} failed: {e}")
            continue
        for p in products:
            pid = str(p.get("id"))
            if pid in seen:  # collections overlap; keep one entry per product
                continue
            seen.add(pid)
            variants = p.get("variants", [])
            chosen = next((v for v in variants if v.get("available")), variants[0] if variants else {})
            try:
                price = float(chosen.get("price"))
            except (TypeError, ValueError):
                price = None
            items.append({
                "retailer": "Bog & Idé",
                "product_id": pid,
                "name": p.get("title", ""),
                "url": f"{BASE}/products/{p.get('handle')}",
                "in_stock": any(v.get("available") for v in variants),
                "price": price,
                "stores_count": None,  # Shopify gives no per-store data
            })
    return items
