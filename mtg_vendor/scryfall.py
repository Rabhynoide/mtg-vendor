"""Correspondance édition + numéro de collection -> identifiant produit Cardmarket, via Scryfall."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from . import cache, http

COLLECTION_URL = "https://api.scryfall.com/cards/collection"
BATCH_SIZE = 75  # limite de l'API Scryfall
CACHE_FILE = "scryfall_ids.json"


def _key(set_code: str, number: str) -> str:
    return f"{set_code.lower()}/{number}"


def resolve_cardmarket_ids(
    printings: Iterable[tuple[str, str]],
    post_json: Callable[[str, Any], Any] | None = None,
    pause: Callable[[], None] | None = None,
    use_cache: bool = True,
) -> dict[tuple[str, str], int | None]:
    """Renvoie {(édition, numéro): idProduct Cardmarket ou None si introuvable}.

    Les identifiants déjà connus sont gardés en cache : ils ne changent pas.
    """
    post_json = post_json or http.post_json
    pause = pause or http.polite_pause
    known: dict[str, int | None] = cache.load_json(CACHE_FILE, {}) if use_cache else {}
    wanted = list(dict.fromkeys((s.lower(), n) for s, n in printings))
    missing = [p for p in wanted if _key(*p) not in known]

    for i in range(0, len(missing), BATCH_SIZE):
        batch = missing[i : i + BATCH_SIZE]
        if i:
            pause()
        response = post_json(
            COLLECTION_URL,
            {"identifiers": [{"set": s, "collector_number": n} for s, n in batch]},
        )
        for card in response.get("data", []):
            known[_key(card["set"], card["collector_number"])] = card.get("cardmarket_id")
        for s, n in batch:
            known.setdefault(_key(s, n), None)

    if use_cache:
        # On ne garde en cache que les réussites, pour réessayer les échecs la fois suivante.
        cache.save_json(CACHE_FILE, {k: v for k, v in known.items() if v is not None})
    return {p: known.get(_key(*p)) for p in wanted}
