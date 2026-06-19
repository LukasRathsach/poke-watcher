# Poké Watcher — setup

Free, fully automatic Pokémon restock watcher. Checks Bilka, BR, Føtex and
Bog & Idé every ~15 minutes and posts a Discord message the moment a product
from a tracked set flips from out-of-stock to in-stock — with set, product,
price, price-per-pack, direct link and time.

## How it runs — GitHub Actions (no laptop needed)

The watcher runs in GitHub's cloud on a schedule (`.github/workflows/watch.yml`),
so it works 24/7 without your Mac being on. Free.

Already wired up:
- Webhook stored as repo secret `DISCORD_WEBHOOK` (never in the code).
- Stock state persists between runs via the Actions cache.
- Sets/keywords/retailers live in `config.example.yaml` (committed).

**To change which sets it tracks:** edit `sets:` in `config.example.yaml`, commit, push.
**To run it on demand:** repo → Actions → "poke-watcher" → Run workflow.
**Logs:** repo → Actions → pick a run.

> Note: GitHub cron can be delayed or skipped under load — expect "within ~15-30 min",
> not to-the-second. Fine for restocks. Private-repo Actions minutes are limited
> (2000/month free); a 15-min cron sits near that — make the repo public for
> unlimited minutes if you ever run low.

## Discord commands (subscribe to a set, get @mentioned)

Anyone in the channel can type (set name is free text):

- `tag mig: prismatic` (or `tag me prismatic`, `!track surging sparks`, `follow 151`)
  — follow a set; you get @mentioned when a product from it restocks.
- `stop tag: prismatic` (or `!untrack 151`) — unfollow.
- `!sets` (or `!list`) — show what's currently followed.

Commands are read each cycle (~15 min), so a new subscription takes effect within
~15 min. Following a set also makes the watcher start tracking it. Needs the bot
secrets set: `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID` (see bot setup).

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
