from . import salling, bogide, coolshop, proshop

# config key -> source module exposing fetch(config) -> list[item dict]
SOURCES = {
    "salling": salling,   # Bilka + BR + Føtex
    "bogide": bogide,     # Bog & Idé (Shopify)
    "coolshop": coolshop,
    "proshop": proshop,
}
