# AI Handoff — Poké Watcher

Last updated: 2026-06-19

## Purpose
Free, fully automatic Pokémon restock notifier for Danish retailers. Posts to a
Discord channel via webhook when sealed product flips out-of-stock -> in-stock.
Runs on Lukas' Mac via launchd. No AI, no server, no paid services.

## Status — WORKING end-to-end
- Pipeline verified live: forced transition fired a real Discord push.
- 4 retailers live via 2 sources (Salling: Bilka/BR/Føtex; Bog & Idé: Shopify).
- ~54 sealed products tracked across stores; baseline seeded.

## Roadmap

### Done
- [x] Discord webhook (replaced ntfy per Lukas) + test push verified
- [x] Salling source (Bilka + BR + Føtex via Algolia)
- [x] Bog & Idé source (Shopify collections)
- [x] Core transition/filter logic + self-check (`test_watch.py`)
- [x] Whole-word keyword match (fixed ETB-in-"sletbar" false positive)
- [x] launchd plist + setup.md
- [x] GitHub repo (private): github.com/LukasRathsach/poke-watcher

### Pending
- [ ] Install launchd job on Lukas' Mac (he runs the 3 commands in setup.md)
- [ ] Confirm real restock ping lands once a sealed product actually restocks
- [ ] (optional) Implement Coolshop source — JSON API exists (`POST /api/search`)
- [ ] (optional) Proshop — needs a real browser (Playwright); currently 403-blocked
- [ ] (optional) Fill `sets:` in config.yaml to narrow to specific sets

## Decisions
- ntfy -> Discord webhook (Lukas' choice, simpler, free).
- Netto excluded: different stack (Next.js), no Pokémon sealed product.
- Broad Algolia/Shopify query "pokemon", then keyword-filter in watch.py — keeps each source dumb.
