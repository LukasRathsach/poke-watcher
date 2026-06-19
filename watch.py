"""One poll cycle: fetch enabled sources, filter to Pokémon items, and push a
Discord message for every product that just went out-of-stock -> in-stock.

Run by launchd every ~12 min. No loop here, no AI, no server."""
import json
import pathlib
import re

import yaml

from notify import notify
from sources import SOURCES

ROOT = pathlib.Path(__file__).parent
CONFIG = ROOT / "config.yaml"
STATE = ROOT / "state.json"


def _hit(words, text):
    # word-boundary match so short keywords like "ETB" don't match inside "sletbar"
    return any(re.search(rf"\b{re.escape(w.lower())}\b", text) for w in words)


def matches(name, type_keywords, sets):
    """Set-first filter. When `sets` is given, the wanted set is the primary gate and
    the product must also be sealed card product (type guard). With no sets, fall back
    to matching any sealed card product. All matches are whole-word."""
    n = name.lower()
    if sets and not _hit(sets, n):
        return False
    return _hit(type_keywords, n)


def transitions(prev_state, items):
    """Pure: items that are in stock now and were absent/out-of-stock before."""
    fired = []
    for it in items:
        key = f"{it['retailer']}:{it['product_id']}"
        if it["in_stock"] and not prev_state.get(key, False):
            fired.append(it)
    return fired


def run():
    cfg = yaml.safe_load(CONFIG.read_text())
    first_run = not STATE.exists()  # first ever run: seed baseline, don't ping
    prev = json.loads(STATE.read_text()) if STATE.exists() else {}
    state = dict(prev)  # start from prior; only successful fetches update it

    items = []
    for name, enabled in cfg.get("retailers", {}).items():
        if not enabled or name not in SOURCES:
            continue
        try:
            fetched = SOURCES[name].fetch(cfg)
        except Exception as e:  # a failing source never kills the cycle
            print(f"[{name}] fetch failed: {e}")
            continue
        kept = [it for it in fetched
                if matches(it["name"], cfg["type_keywords"], cfg.get("sets") or [])]
        items += kept
        # update state only for what this (successful) source actually returned
        for it in kept:
            state[f"{it['retailer']}:{it['product_id']}"] = it["in_stock"]

    fired = [] if first_run else transitions(prev, items)
    for it in fired:
        try:
            notify(cfg["discord_webhook"], it["name"], it["retailer"], it["url"])
            print(f"NOTIFY: {it['name']} @ {it['retailer']}")
        except Exception as e:
            print(f"[notify] failed for {it['name']}: {e}")

    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    tag = " (baseline seeded, no pings)" if first_run else ""
    print(f"cycle done: {len(items)} matched items, {len(state)} tracked{tag}")


if __name__ == "__main__":
    run()
