"""Read recent Discord channel messages (bot token) and turn subscription commands
into per-set @mention lists. No AI — plain text parsing. Called by watch.py each cycle.

Commands anyone can type in the channel (set name is free text):
  tag mig: prismatic      / tag me prismatic   -> follow a set, get @mentioned on restock
  !track surging sparks    / follow 151
  stop tag: prismatic      / !untrack 151       -> unfollow
  !sets  /  !list  /  !help                     -> show what's tracked
"""
import re
import requests

API = "https://discord.com/api/v10"

ADD = re.compile(r"^\s*(?:tag\s+(?:mig|me)|!?track|!?follow|abonner\w*)\s*[:\-]?\s+(.+)", re.I)
REMOVE = re.compile(r"^\s*(?:stop\s+tag\w*|!?untrack|!?unfollow|fjern)\s*[:\-]?\s+(.+)", re.I)
LIST = re.compile(r"^\s*!?(sets|list|liste|help|hjælp|hjaelp)\s*$", re.I)


def _clean_set(s):
    return s.strip().strip('"').strip("'").lower()[:40]


def parse(content):
    """(action, set_token) for one message. action in {add, remove, list, None}."""
    m = ADD.match(content)
    if m:
        return "add", _clean_set(m.group(1))
    m = REMOVE.match(content)
    if m:
        return "remove", _clean_set(m.group(1))
    if LIST.match(content):
        return "list", None
    return None, None


def poll(token, channel_id, subs, last_id):
    """Read new messages, apply commands. Returns (subs, last_id, replies).

    subs: {set_token: [user_id, ...]}. First run (last_id falsy) only records the
    newest message id so we never replay pre-bot history."""
    headers = {"Authorization": f"Bot {token}"}
    params = {"limit": 100}
    if last_id:
        params["after"] = str(last_id)
    r = requests.get(f"{API}/channels/{channel_id}/messages",
                     headers=headers, params=params, timeout=15)
    r.raise_for_status()
    msgs = sorted(r.json(), key=lambda m: int(m["id"]))  # oldest -> newest

    if not last_id:  # initialise: skip backlog, start listening from now
        return subs, (msgs[-1]["id"] if msgs else last_id), []

    replies = []
    for m in msgs:
        last_id = m["id"]
        if m.get("author", {}).get("bot"):
            continue
        uid = m["author"]["id"]
        action, token_set = parse(m.get("content", ""))
        if action == "add" and token_set:
            users = subs.setdefault(token_set, [])
            if uid not in users:
                users.append(uid)
            replies.append(f"<@{uid}> følger nu **{token_set.title()}** — jeg tagger dig når det kommer på lager.")
        elif action == "remove" and token_set:
            users = subs.get(token_set, [])
            if uid in users:
                users.remove(uid)
                if not users:
                    subs.pop(token_set, None)
            replies.append(f"<@{uid}> følger ikke længere **{token_set.title()}**.")
        elif action == "list":
            if subs:
                lines = "\n".join(f"• **{s.title()}** ({len(u)})" for s, u in sorted(subs.items()))
                replies.append(f"Fulgte sæt:\n{lines}")
            else:
                replies.append("Ingen følger noget endnu. Skriv fx `tag mig: prismatic`.")
    return subs, last_id, replies


if __name__ == "__main__":
    assert parse("tag mig: prismatic") == ("add", "prismatic")
    assert parse("tag me Surging Sparks") == ("add", "surging sparks")
    assert parse("!track 151") == ("add", "151")
    assert parse("follow destined rivals") == ("add", "destined rivals")
    assert parse("stop tag: prismatic") == ("remove", "prismatic")
    assert parse("!untrack 151") == ("remove", "151")
    assert parse("!sets") == ("list", None)
    assert parse("hej alle sammen") == (None, None)
    print("ok")
