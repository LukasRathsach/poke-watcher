# Build Instructions — Poké Watcher

> You are the LLM tasked with **building** this project. Lukas (the owner) has
> already scoped it. Read this whole file, then **start with the onboarding QA
> in step 0 before writing any code.** Build lazily: stdlib + `requests` only,
> shortest thing that works, no frameworks. No LLM calls at runtime — this is a
> plain scheduled program.

## What this is

A standalone Python program that runs on Lukas' Mac on a schedule (`launchd`,
every ~10–15 min), checks selected Danish retailers for **Pokémon booster
packs / displays / Elite Trainer Boxes (ETB)**, and sends a **push to his phone
via [ntfy.sh](https://ntfy.sh)** the moment an item flips from out-of-stock →
in-stock. No tokens, no AI at runtime, no server — just a cron-style script.

## Retailer scope (v1)

- **Salling Group** — one integration covers **BR, Bilka, Føtex, Netto** (shared
  e-commerce backend). Do this one first; it's the highest-leverage source.
- **Proshop** — separate scraper.
- **Coolshop** — separate scraper.

## Step 0 — Onboarding QA (DO THIS FIRST, in the first session)

Before writing any code, run a short guided interview with Lukas — **one
question at a time**, wait for each answer (he prefers QA over assumptions, and
is happy to paste raw data like a product URL or a network response). Collect:

1. **ntfy topic** — pick/confirm a hard-to-guess topic name (e.g.
   `poke-stock-<random>`), and confirm he's installed the ntfy app and
   subscribed to it. (ntfy needs no account; the topic name IS the secret.)
2. **Poll interval** — default 12 min. Confirm or change.
3. **Product-type keywords** — confirm the match list: `booster`, `display`,
   `elite trainer box`, `ETB`, `booster bundle`. Add/remove per his wishes.
4. **Named sets** — ask if he wants to track specific sets now or leave empty.
   The config supports a `sets:` list; empty = match any product whose
   type-keywords hit. He has said he'll fill set names in later, so empty is a
   fine default.
5. **Retailers to enable now** — default all three (Salling, Proshop, Coolshop).

Write the answers into `config.yaml` (copy from `config.example.yaml`), then
proceed to build. Do **not** commit `config.yaml` (it holds the ntfy topic) —
add it to `.gitignore`.

## Step 1 — Discover the data sources (the real risk; do before coding logic)

None of these retailers is guaranteed to have a clean public stock API. Your
**first build task** is discovery, per source:

- Open a Pokémon product/category page in a browser, open DevTools → Network,
  and find the request that returns product + availability data (usually a JSON
  XHR/fetch). Prefer that JSON endpoint over scraping rendered HTML.
- For **Salling**: investigate whether the Bilka/Føtex/BR/Netto storefronts call
  a shared product/search API (look for a host like `*.sallinggroup.com` or an
  internal `/api/` product-search returning availability). There is also a
  public Salling Group developer API (`api.sallinggroup.com`) — check whether it
  exposes product availability with a free token; if not, fall back to the
  storefront's own JSON endpoint.
- For **Proshop** / **Coolshop**: find their category/search JSON; if only HTML
  is available, scrape with `requests` + a small HTML parser (`html.parser` from
  stdlib, or `selectorlib`/`beautifulsoup4` if genuinely needed — justify any
  new dep).

Document each discovered endpoint inline in the relevant `sources/*.py` module
(a one-line comment naming the endpoint and what it returns).

If a source actively blocks automated access or has no usable endpoint, say so,
ship the working sources, and leave a `# ponytail:` note on the stub rather than
faking it.

## Step 2 — Architecture (keep it this small)

```
poke-watcher/
  watch.py                # entrypoint: orchestrate one poll cycle
  notify.py               # POST to ntfy.sh/<topic>
  sources/
    __init__.py           # registry: list of enabled source functions
    salling.py            # BR + Bilka + Føtex + Netto
    proshop.py
    coolshop.py
  config.yaml             # gitignored; created in step 0
  config.example.yaml     # committed template
  state.json              # gitignored; last-seen stock state
  com.lukas.pokewatcher.plist  # launchd job
  setup.md                # how to install the launchd job + ntfy app
```

**Source contract** — every `sources/*.py` exposes:

```python
def fetch(config) -> list[dict]:
    # returns items: {"retailer": str, "product_id": str,
    #                 "name": str, "url": str, "in_stock": bool}
```

`product_id` must be stable per product (use the retailer's own SKU/id).

**Filtering** (`watch.py`): keep an item only if its name matches a
product-type keyword from config AND (the `sets` list is empty OR the name
contains one of the set names). Case-insensitive.

**State + notification logic** (the core, write a self-check for it):
- Load `state.json` → `{ "<retailer>:<product_id>": in_stock_bool }`.
- For each filtered item: if it is `in_stock=True` now and was `False`/absent
  before → **notify**. Otherwise no notification.
- Save the new full state at the end of the cycle.
- This guarantees: one ping per restock event, no repeats until it sells out and
  returns.

**Notification** (`notify.py`): `POST https://ntfy.sh/<topic>` with a title like
`Pokémon in stock` and body `"<name> @ <retailer>"`, and set the `Click` header
to the product URL so tapping the push opens the page. Use the `X-Title` /
`Click` / `X-Tags` ntfy headers.

## Step 3 — Politeness & robustness (do not skip)

- Realistic interval (default 12 min — set via launchd, not a `while` loop).
- A descriptive `User-Agent`; respect each site's `robots.txt`.
- Timeout on every request; wrap each source in try/except so one failing source
  never kills the cycle — log the error, skip that source, continue.
- Exponential backoff / skip on HTTP 429 or 5xx.
- Never notify on an error or an empty fetch (an empty result ≠ everything went
  out of stock — only transitions from a known in-stock=False to True count).

## Step 4 — Scheduling

Provide `com.lukas.pokewatcher.plist` (a `launchd` `StartInterval` job, ~720s)
that runs `python3 watch.py` from the project dir, plus `setup.md` with the
`launchctl load` command and the ntfy phone-app setup.

## Step 5 — Verify before declaring done

- One runnable self-check (`assert`-based `__main__` or one `test_*.py`) on the
  transition logic in `watch.py`: feed it a fake prior state + fake current
  items and assert it notifies exactly on out→in transitions and never twice.
- Do at least one real end-to-end run against the live sources and confirm a
  test push lands on Lukas' phone (send one manual test notification via
  `notify.py` during onboarding so he sees it works early).

## Constraints recap

- Python 3, stdlib + `requests` (+ a YAML reader, e.g. `pyyaml`). Justify any
  further dependency.
- No AI/LLM at runtime. No hosted server. Runs entirely on Lukas' Mac.
- `config.yaml` and `state.json` are gitignored.
- Lazy first: the smallest implementation that reliably fires the right push.
