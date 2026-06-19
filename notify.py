"""Send a restock push to a Discord channel via an incoming webhook."""
import requests


def notify(webhook, name, retailer, url):
    requests.post(
        webhook,
        timeout=15,
        json={
            "username": "Poké Watcher",
            "content": f"🟢 **{name}** er på lager hos **{retailer}**\n{url}",
        },
    ).raise_for_status()


if __name__ == "__main__":
    # Manual test push: python3 notify.py
    import yaml, pathlib
    cfg = yaml.safe_load(pathlib.Path("config.yaml").read_text())
    notify(cfg["discord_webhook"], "Testprodukt", "Test", "https://example.com")
    print("Test push sent.")
