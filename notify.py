"""Send a restock push to a Discord channel via an incoming webhook.

The message is a Discord embed showing set, product, price, price-per-pack,
a direct link (the embed title), and when the restock was detected."""
import requests

GREEN = 0x2ECC71


def _kr(v):
    if v is None:
        return "?"
    return f"{int(v)} kr" if float(v).is_integer() else f"{v:.2f} kr"


def notify(webhook, *, name, retailer, url, set_name, price, packs, exact_packs, when,
           mentions=None):
    mentions = mentions or []
    fields = [
        {"name": "Sæt", "value": (set_name or "—").title(), "inline": True},
        {"name": "Butik", "value": retailer, "inline": True},
        {"name": "Pris", "value": _kr(price), "inline": True},
    ]
    if packs and price:
        prefix = "" if exact_packs else "~"  # ~ marks a type-based pack estimate
        per = int(round(price / packs))
        fields.append({"name": "Pris pr. pakke",
                       "value": f"{prefix}{per} kr ({packs} pk)", "inline": True})
    payload = {
        "username": "Poké Watcher",
        "content": " ".join(f"<@{u}>" for u in mentions) or None,
        "allowed_mentions": {"parse": [], "users": mentions},  # only ping these users
        "embeds": [{
            "title": name,
            "url": url,
            "color": GREEN,
            "fields": fields,
            "footer": {"text": f"Restock • {when}"},
        }],
    }
    requests.post(webhook, timeout=15, json=payload).raise_for_status()


def send_text(webhook, text):
    """Plain channel message (command confirmations). Never pings roles/@everyone."""
    requests.post(webhook, timeout=15, json={
        "username": "Poké Watcher", "content": text,
        "allowed_mentions": {"parse": ["users"]},
    }).raise_for_status()


if __name__ == "__main__":
    # Manual test push: python3 notify.py
    import os, yaml, pathlib, datetime
    cfg = yaml.safe_load(pathlib.Path("config.yaml").read_text())
    webhook = os.environ.get("DISCORD_WEBHOOK") or cfg["discord_webhook"]
    notify(webhook, name="Pokémon ETB SV8 Surging Sparks", retailer="Bilka",
           url="https://www.bilka.dk", set_name="Surging Sparks", price=349.0,
           packs=9, exact_packs=False,
           when=datetime.datetime.now().strftime("%d-%m-%Y %H:%M"))
    print("Test push sent.")
