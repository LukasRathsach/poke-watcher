# Coolshop exposes a JSON API (POST https://www.coolshop.dk/api/search, plus
# /api/products/). Request shape is reverse-engineered below; filled in after the
# Salling slice was verified working.
import requests

UA = "poke-watcher (personal restock notifier; github.com/LukasRathsach/poke-watcher)"


def fetch(config):
    # ponytail: implemented after verifying the live request/response shape below.
    return []
