# Poké Watcher — setup

Free, fully automatic Pokémon restock watcher. Polls Bilka, BR, Føtex and
Bog & Idé roughly every 30 seconds and posts a Discord message the moment a
product from a tracked set flips from out-of-stock to in-stock — with set,
product, price, price-per-pack, physical-store count, direct link and time.

## How it runs — GitHub Actions (no laptop needed)

Runs in GitHub's cloud (`.github/workflows/watch.yml`), 24/7 without your Mac.
Free (public repo = unlimited Actions minutes). It's a self-looping job: each run
polls every ~30s for ~28 min, and a cron restarts it every 30 min — so coverage
is effectively continuous.

Already wired up:
- Webhook + Supabase keys stored as repo secrets (never in the code).
- Stock state persists across loop restarts via the Actions cache.
- Sets/keywords/retailers live in `config.example.yaml` (committed).

**To change which sets it tracks:** edit `sets:` in `config.example.yaml`, commit, push.
**To run it on demand:** repo → Actions → "poke-watcher" → Run workflow.
**Logs:** repo → Actions → pick a run.

> ~30s is the polite/safe floor — polling the retailers' APIs harder risks getting
> rate-limited or blocked. A drop that sells out in under ~30s can still be missed.

## Discord slash commands (subscribe to a set, get @mentioned)

Instant — handled by a Vercel endpoint (`bot/api/interactions.js`), not the poll loop:

- `/track set:<navn>` — follow a set (autocomplete suggests available sets); you get
  @mentioned when a product from it restocks. Following a set also starts tracking it.
- `/untrack set:<navn>` — unfollow.
- `/mysets` — what you follow. `/sets` — everything you can follow.

Subscriptions live in Supabase (`pokewatcher_*` tables, claude-invest project); the
poll loop reads them each cycle to know who to @mention.

## Optional: also run locally via launchd

Only runs while the Mac is on (asleep catches up on wake; off pauses it). Redundant
with the cloud job — skip unless you want a local copy.

## What's already done

- `config.yaml` holds your Discord webhook (gitignored — never pushed).
- `.venv/` has the only two dependencies (`requests`, `pyyaml`).
- `state.json` holds the last-seen stock state (gitignored, auto-created).

## Install the scheduler (one time)

```bash
cd ~/Desktop/Projects/Personal/poke-watcher
cp com.lukas.pokewatcher.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.lukas.pokewatcher.plist
```

That's it. It now runs every 12 min and on every login. Output is logged to
`watch.log` in this folder.

Check it's loaded:

```bash
launchctl list | grep pokewatcher
```

## Stop / restart it

```bash
launchctl unload ~/Library/LaunchAgents/com.lukas.pokewatcher.plist   # stop
launchctl load   ~/Library/LaunchAgents/com.lukas.pokewatcher.plist   # start
```

After editing the `.plist`, you must `unload` then `load` again.

## Run one cycle by hand (to test)

```bash
.venv/bin/python watch.py        # one poll cycle; pings on a real restock
.venv/bin/python notify.py       # sends a test push to your Discord
```

## Tune what it watches — `config.yaml`

- `type_keywords` — product types to match (case-insensitive, whole-word):
  `booster`, `booster bundle`, `display`, `elite trainer box`, `ETB`.
- `sets` — optional. Empty = match any sealed product. Add set names to narrow,
  e.g. `["Prismatic Evolutions", "Surging Sparks"]` — then it only pings for
  those sets.
- `retailers` — toggle sources on/off.

No restart needed after editing config — the next cycle picks it up.

## Notes / limits

- Runs only while the Mac is on. Asleep is fine (it catches up on wake);
  powered off pauses it until you turn it back on.
- First run seeds a baseline silently (no ping flood). Pings start from the
  next restock event onward.
- One ping per restock event — no repeats until it sells out and returns.
- **Coolshop**: JSON API exists but not implemented yet (`coolshop: false`).
- **Proshop**: bot-blocked (HTTP 403), stub only. Needs a real browser to scrape.
- **Netto**: deliberately excluded (different stack, no Pokémon sealed product).
