"""Suivi des cartes déjà mises en vente, pour ne pas créer de doublons d'une session à l'autre."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .moxfield import Card
from .pricing import PricedCard

DEFAULT_PATH = Path("mises_en_vente.json")


def card_key(card: Card) -> str:
    return "|".join([
        card.set_code, card.collector_number, card.language, card.condition,
        "etched" if card.etched else "foil" if card.foil else "normal",
    ])


class ListingLedger:
    """Fichier JSON : clé de la carte -> quantité déjà mise en vente et date."""

    def __init__(self, path: str | Path = DEFAULT_PATH):
        self.path = Path(path)
        self.entries: dict[str, dict] = {}
        if self.path.exists():
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))

    def listed_quantity(self, card: Card) -> int:
        return self.entries.get(card_key(card), {}).get("quantite", 0)

    def remaining(self, priced: list[PricedCard]) -> list[PricedCard]:
        """Ne garde que les cartes pas encore (ou pas entièrement) mises en vente, avec la quantité restante."""
        from dataclasses import replace

        out = []
        for p in priced:
            left = p.card.quantity - self.listed_quantity(p.card)
            if left > 0:
                out.append(p if left == p.card.quantity else replace(p, card=replace(p.card, quantity=left)))
        return out

    def record(self, items: list[PricedCard]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for p in items:
            key = card_key(p.card)
            entry = self.entries.setdefault(key, {"nom": p.card.name, "quantite": 0})
            entry["quantite"] += p.card.quantity
            entry["prix"] = str(p.price)
            entry["date"] = now
        self.save()

    def save(self) -> None:
        self.path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2), encoding="utf-8")
