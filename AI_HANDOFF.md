# AI Handoff — Poké Watcher

Last updated: 2026-06-20

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

- [x] Set-first filtering; tracking 7 sought-after sets (Prismatic, 151, Ascended
  Heroes, Surging Sparks, Destined Rivals, Paldean Fates, Phantasmal)
- [x] Rich notification: set, product, price, price-per-pack (estimated by type), link, DK time
- [x] **Cloud deploy: GitHub Actions cron** (~15 min) — runs without laptop; state via cache; webhook = repo secret

- [x] Discord commands: friends type "tag mig: <set>" to follow a set + get @mentioned
  on restock. Bot reads channel each cycle (discord_read.py); subs persist in cache.

### Pending
- [ ] Add bot secrets `DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID` (Lukas creating the bot)
- [ ] Live-test a command ("tag mig: prismatic") + a mention on restock
- [ ] Confirm first cloud run seeds baseline + a later run pings on a real restock
- [ ] (optional) Implement Coolshop source — JSON API exists (`POST /api/search`)
- [ ] (optional) Proshop — needs a real browser (Playwright); currently 403-blocked
- [ ] (optional) Add "Pitch Black" (= JP Abyss Eye) set token once it launches in EN
- [ ] (optional) Refine pack-count estimates per set if box sizes differ from SV defaults

## Decisions
- ntfy -> Discord webhook (Lukas' choice, simpler, free).
- Netto excluded: different stack (Next.js), no Pokémon sealed product.
- Broad Algolia/Shopify query "pokemon", then keyword-filter in watch.py — keeps each source dumb.
