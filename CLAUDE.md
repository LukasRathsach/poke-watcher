# Poké Watcher

Standalone Python program that checks Danish retailers for Pokémon sealed product
(booster / display / ETB) every ~12 min and posts a Discord message when an item
flips out-of-stock -> in-stock. No AI at runtime, no server.

## Stack
- Python 3, stdlib + `requests` + `pyyaml` only. `.venv/` in repo root.
- No framework. Lazy / shortest-working-diff (ponytail).

## Deployment
- Runs on Lukas' Mac via `launchd` (`com.lukas.pokewatcher.plist`, StartInterval 720s).
- **Secrets:** Discord webhook lives in `config.yaml` (gitignored). No cloud, no env-var dashboard.
- `state.json` (gitignored) holds last-seen stock; auto-created. First run seeds baseline silently.

## Run / test
- `.venv/bin/python watch.py` — one poll cycle.
- `.venv/bin/python test_watch.py` — self-check on transition + keyword logic.
- `.venv/bin/python notify.py` — manual Discord test push.

## Architecture
- `watch.py` — orchestrates a cycle: fetch enabled sources, keyword-filter, fire pings on out->in, save state.
- `notify.py` — POST to Discord webhook.
- `sources/*.py` — each exposes `fetch(config) -> list[{retailer, product_id, name, url, in_stock}]`.

## Sources
- `salling.py` — Bilka + BR + Føtex via public Algolia index (`prod_<STORE>_PRODUCTS`). WORKING.
- `bogide.py` — Bog & Idé via Shopify `/collections/{pokemon,pokemon-tcg}/products.json`. WORKING.
- `coolshop.py` — stub. JSON API exists (`POST /api/search`), not implemented.
- `proshop.py` — stub. Bot-blocked (403).

## Gotchas
- Keyword match is **whole-word** (regex `\b`): naive substring made "ETB" match Danish "sl**etb**ar" (erasable). Don't revert to `in`.
- Never notify on empty/failed fetch — only on a known False->True transition.
- Adding a new source after baseline: re-seed (`rm state.json && python watch.py`) so it doesn't ping-flood.
