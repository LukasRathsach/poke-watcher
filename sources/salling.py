# Salling Group storefronts (Bilka, BR, Føtex) expose their full product catalogue
# through a public Algolia search index — the same search-only key the websites ship
# to the browser. One POST per store returns name + stable product id + live online
# stock (is_in_stock_online). Endpoint:
#   POST https://{APP}-dsn.algolia.net/1/indexes/{index}/query
import requests

ALGOLIA_APP = "DRP4O45G5T"
ALGOLIA_KEY = "f3a34fc94874579eaf3cd39fef660948"  # public search-only key (from bilka.dk)

# store name -> (algolia product index, storefront base for relative product urls)
STORES = {
    "Bilka": ("prod_BILKA_PRODUCTS", "https://www.bilka.dk"),
    "BR": ("prod_BR_PRODUCTS", "https://www.br.dk"),
    "Føtex": ("prod_FOETEX_PRODUCTS", "https://www.foetex.dk"),
}

UA = "poke-watcher (personal restock notifier; github.com/LukasRathsach/poke-watcher)"


def _search(index):
    url = f"https://{ALGOLIA_APP}-dsn.algolia.net/1/indexes/{index}/query"
    r = requests.post(
        url,
        timeout=15,
        headers={
            "X-Algolia-API-Key": ALGOLIA_KEY,
            "X-Algolia-Application-Id": ALGOLIA_APP,
            "User-Agent": UA,
        },
        json={"params": "query=pokemon&hitsPerPage=200"},
    )
    r.raise_for_status()
    return r.json().get("hits", [])


def fetch(config):
    items = []
    for store, (index, base) in STORES.items():
        try:
            hits = _search(index)
        except Exception as e:  # one failing store must not kill the others
            print(f"[salling] {store} failed: {e}")
            continue
        for h in hits:
            url = h.get("product_url") or h.get("canonical_url") or ""
            if url.startswith("/"):
                url = base + url
            items.append({
                "retailer": store,
                "product_id": str(h.get("id") or h.get("objectID")),
                "name": h.get("name", ""),
                "url": url,
                "in_stock": bool(h.get("is_in_stock_online")),
            })
    return items
