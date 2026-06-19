# ponytail: stub. Proshop actively blocks automated access (HTTP 403 on the search
# page even with full browser headers — bot protection). No usable JSON endpoint was
# found during discovery. Not faking it. Upgrade path: drive a real browser
# (Playwright) or find an unprotected mobile/app API, then return the same item dicts.
def fetch(config):
    return []
