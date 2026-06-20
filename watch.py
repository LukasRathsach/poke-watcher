"""One poll cycle: fetch enabled sources, filter to Pokémon items, and push a
Discord message for every product that just went out-of-stock -> in-stock.

Run on a schedule (GitHub Actions cron, or launchd). No loop, no AI, no server."""
import datetime
import json
import os
import pathlib
import re

import yaml

import store
from notify import notify, alert
from sources import SOURCES

ROOT = pathlib.Path(__file__).parent
CONFIG = ROOT / "config.yaml"          # local (gitignored, holds webhook)
CONFIG_FALLBACK = ROOT / "config.example.yaml"  # committed; used in CI
STATE = ROOT / "state.json"
HEALTH = ROOT / "health.json"          # heartbeat: per-source fail streak + alerted flag
HEALTH_THRESHOLD = 3                   # consecutive bad cycles before alerting


def _now_dk():
    # CI runners are UTC; show Danish wall-clock time in the notification
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Copenhagen"))
    except Exception:
        return datetime.datetime.now()


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


def matched_set(name, sets):
    """The wanted set token (as stored, lowercased) this product belongs to, else None.
    Returned raw so subscriptions can be looked up by token; display title-cases it."""
    n = name.lower()
    for s in sets:
        if _hit([s], n):
            return s
    return None


def pack_count(name):
    """(packs, exact). Booster packs in the product. exact=True when the name states
    a count; False when estimated from the product type (ETB/bundle/box/tin defaults).
    ponytail: SV-era defaults — tweak if a set's box sizes differ."""
    n = name.lower()
    m = re.search(r"(\d+)\s*-?\s*(?:pak|pack|pakke)\b", n)
    if m:
        return int(m.group(1)), True
    for w, v in (("triple", 3), ("double", 2), ("single", 1)):
        if re.search(rf"\b{w}\s+pack\b", n):
            return v, True
    if "booster box" in n:
        return 36, False
    if "booster bundle" in n:
        return 6, False
    if re.search(r"\belite trainer box\b|\betb\b", n):
        return 9, False
    if "blister" in n:
        return 3, False
    if "mini tin" in n or re.search(r"\btin\b", n):
        return 2, False
    if re.search(r"\bbooster\b", n):
        return 1, False
    return None, False


def check_health(health, name, ok, send):
    """Heartbeat: alert once when a source has failed HEALTH_THRESHOLD cycles in a row
    (0 products or an error — almost always a rotated key / changed endpoint), and once
    when it recovers. `send` is a callable(text). Mutates `health` in place."""
    h = health.setdefault(name, {"fails": 0, "alerted": False})
    if ok:
        if h["alerted"]:
            send(f"✅ Poké Watcher: kilden **{name}** virker igen.")
        h["fails"], h["alerted"] = 0, False
    else:
        h["fails"] += 1
        if h["fails"] >= HEALTH_THRESHOLD and not h["alerted"]:
            send(f"⚠️ Poké Watcher: kilden **{name}** har fejlet {h['fails']} cyklusser i "
                 f"træk (0 produkter eller fejl). Tjek om endpoint/nøgle er ændret.")
            h["alerted"] = True


def transitions(prev_state, items):
    """Pure: items that are in stock now and were absent/out-of-stock before."""
    fired = []
    for it in items:
        key = f"{it['retailer']}:{it['product_id']}"
        if it["in_stock"] and not prev_state.get(key, False):
            fired.append(it)
    return fired


def run():
    cfg = yaml.safe_load((CONFIG if CONFIG.exists() else CONFIG_FALLBACK).read_text())
    webhook = os.environ.get("DISCORD_WEBHOOK") or cfg.get("discord_webhook")
    heartbeat_hook = os.environ.get("HEARTBEAT_WEBHOOK") or webhook  # private channel if set
    health = json.loads(HEALTH.read_text()) if HEALTH.exists() else {}

    # per-set subscriptions come from Supabase (written by the /track slash command)
    try:
        subs = store.load_subscriptions()
    except Exception as e:
        print(f"[store] subscription load failed: {e}")
        subs = {}

    # effective sets = config sets + any set someone subscribed to via /track
    sets = list(dict.fromkeys((cfg.get("sets") or []) + list(subs.keys())))
    first_run = not STATE.exists()  # first ever run: seed baseline, don't ping
    prev = json.loads(STATE.read_text()) if STATE.exists() else {}
    state = dict(prev)  # start from prior; only successful fetches update it

    items = []
    for name, enabled in cfg.get("retailers", {}).items():
        if not enabled or name not in SOURCES:
            continue
        try:
            fetched = SOURCES[name].fetch(cfg)
            ok = len(fetched) > 0  # 0 products = almost certainly a broken source
        except Exception as e:  # a failing source never kills the cycle
            print(f"[{name}] fetch failed: {e}")
            fetched, ok = [], False
        try:
            check_health(health, name, ok, lambda t: alert(heartbeat_hook, t))
        except Exception as e:
            print(f"[heartbeat] {name}: {e}")
        kept = [it for it in fetched
                if matches(it["name"], cfg["type_keywords"], sets)]
        items += kept
        # update state only for what this (successful) source actually returned
        for it in kept:
            state[f"{it['retailer']}:{it['product_id']}"] = it["in_stock"]

    fired = [] if first_run else transitions(prev, items)
    when = _now_dk().strftime("%d-%m-%Y %H:%M")
    for it in fired:
        packs, exact = pack_count(it["name"])
        set_token = matched_set(it["name"], sets)
        try:
            notify(webhook, name=it["name"], retailer=it["retailer"], url=it["url"],
                   set_name=set_token, price=it.get("price"),
                   packs=packs, exact_packs=exact, when=when,
                   mentions=subs.get(set_token, []), stores_count=it.get("stores_count"))
            print(f"NOTIFY: {it['name']} @ {it['retailer']}")
        except Exception as e:
            print(f"[notify] failed for {it['name']}: {e}")

    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    HEALTH.write_text(json.dumps(health, ensure_ascii=False, indent=2))
    tag = " (baseline seeded, no pings)" if first_run else ""
    print(f"cycle done: {len(items)} matched items, {len(state)} tracked{tag}")


if __name__ == "__main__":
    run()
