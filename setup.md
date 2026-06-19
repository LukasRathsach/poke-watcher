# Poké Watcher — setup

Free, fully automatic Pokémon restock watcher. Checks Bilka, BR, Føtex and
Bog & Idé every 12 minutes and posts to a Discord channel the moment a sealed
product (booster / display / ETB) flips from out-of-stock to in-stock.

No accounts, no API costs, no AI, no server — runs on your Mac via `launchd`.

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
