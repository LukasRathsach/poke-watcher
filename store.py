"""Read Pokémon-set subscriptions from Supabase (written by the Vercel slash-command
endpoint). The cron uses this to know who to @mention on a restock. Read-only here."""
import os
import requests

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")


def enabled():
    return bool(URL and KEY)


def load_subscriptions():
    """{set_token: [user_id, ...]} from pokewatcher_subscriptions. {} if not configured."""
    if not enabled():
        return {}
    r = requests.get(
        f"{URL}/rest/v1/pokewatcher_subscriptions",
        params={"select": "set_token,user_id"},
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
        timeout=15,
    )
    r.raise_for_status()
    subs = {}
    for row in r.json():
        subs.setdefault(row["set_token"], []).append(row["user_id"])
    return subs
