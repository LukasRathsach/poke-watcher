"""Self-check for the core notification logic: fire exactly on out->in, never twice.
Run: python3 test_watch.py"""
from watch import transitions, matches, pack_count, matched_set


def item(rid, pid, in_stock, name="Pokémon Booster"):
    return {"retailer": rid, "product_id": pid, "name": name, "url": "u", "in_stock": in_stock}


def test_transitions():
    # absent before + in stock now -> fire
    assert transitions({}, [item("Bilka", "1", True)]) == [item("Bilka", "1", True)]
    # known out-of-stock -> in stock -> fire
    assert transitions({"Bilka:1": False}, [item("Bilka", "1", True)])
    # already in stock -> no fire (no repeat ping)
    assert transitions({"Bilka:1": True}, [item("Bilka", "1", True)]) == []
    # in stock -> out of stock -> no fire
    assert transitions({"Bilka:1": True}, [item("Bilka", "1", False)]) == []
    # empty fetch never fires (error/empty != everything sold out)
    assert transitions({"Bilka:1": True}, []) == []


def test_matches():
    kw = ["booster", "elite trainer box", "ETB"]
    assert matches("Pokémon Booster Bundle", kw, [])
    assert matches("Pokémon Elite Trainer Box", kw, [])
    assert not matches("Pokémon Plush Pikachu", kw, [])
    # word boundaries: "ETB" must NOT match inside the Danish word "sletbar"
    assert not matches("Pokémon sletbar kuglepen", kw, [])
    assert matches("Pokémon ETB Surging Sparks", kw, [])
    # sets filter: only match when a set name is present
    assert matches("Pokémon Booster Prismatic Evolutions", kw, ["Prismatic Evolutions"])
    assert not matches("Pokémon Booster Surging Sparks", kw, ["Prismatic Evolutions"])


def test_pack_count():
    # explicit count in name wins, marked exact
    assert pack_count("Pokémon Stellar Crown blister 3-pak") == (3, True)
    assert pack_count("Temporal Forces Triple Pack") == (3, True)
    # type-based estimates, marked not-exact
    assert pack_count("Pokémon Destined Rivals Elite Trainer Box") == (9, False)
    assert pack_count("Pokémon Booster Bundle Phantasmal") == (6, False)
    assert pack_count("Pokémon 151 Mini Tin") == (2, False)
    assert pack_count("Pokémon TCG booster pack") == (1, False)
    assert pack_count("Pokémon Prismatic Special Collection") == (None, False)


def test_matched_set():
    assert matched_set("Pokémon rivals booster pokemonkort", ["rivals", "151"]) == "Rivals"
    assert matched_set("Pokémon 151 Mini Tin", ["rivals", "151"]) == "151"
    assert matched_set("Pokémon Booster Bundle", ["rivals"]) is None


if __name__ == "__main__":
    test_transitions()
    test_matches()
    test_pack_count()
    test_matched_set()
    print("ok")
