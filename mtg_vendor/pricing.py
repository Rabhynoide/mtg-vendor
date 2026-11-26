"""Association des cartes à Cardmarket et calcul du prix de vente."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .cardmarket_data import CardmarketCatalog
from .moxfield import Card

MIN_PRICE = Decimal("0.02")  # prix minimum accepté par Cardmarket


@dataclass(frozen=True)
class PricedCard:
    card: Card
    id_product: int | None
    id_expansion: int | None
    cardmarket_name: str | None
    price: Decimal | None
    source: str  # "avg30", "trend (pas de moyenne 30 j)", ou la raison de l'échec

    @property
    def ok(self) -> bool:
        return self.price is not None


def _round(value: Decimal) -> Decimal:
    return max(MIN_PRICE, value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def price_card(card: Card, id_product: int | None, catalog: CardmarketCatalog) -> PricedCard:
    if id_product is None:
        return PricedCard(card, None, None, None, None, "introuvable sur Scryfall/Cardmarket")
    product = catalog.products.get(id_product)
    prices = catalog.prices.get(id_product)
    id_expansion = product.id_expansion if product else None
    name = product.name if product else None
    if prices is None:
        return PricedCard(card, id_product, id_expansion, name, None, "pas de prix dans le guide Cardmarket")

    avg30, trend = (prices.avg30_foil, prices.trend_foil) if card.foil else (prices.avg30, prices.trend)
    if avg30:
        return PricedCard(card, id_product, id_expansion, name, _round(avg30), "avg30")
    if trend:
        return PricedCard(card, id_product, id_expansion, name, _round(trend), "trend (pas de moyenne 30 j)")
    return PricedCard(card, id_product, id_expansion, name, None, "aucun prix connu")


def price_all(cards: list[Card], ids: dict[tuple[str, str], int | None], catalog: CardmarketCatalog) -> list[PricedCard]:
    return [price_card(c, ids.get((c.set_code, c.collector_number)), catalog) for c in cards]


COLUMNS = [
    "Nom", "Édition", "Numéro", "Quantité", "Langue", "État", "Foil",
    "idProduct", "idExpansion", "Nom Cardmarket", "Prix", "Source du prix", "Prix d'achat",
]


def write_report(priced: list[PricedCard], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for p in priced:
            c = p.card
            w.writerow([
                c.name, c.set_code, c.collector_number, c.quantity, c.language, c.condition,
                "oui" if c.foil else "", p.id_product or "", p.id_expansion or "", p.cardmarket_name or "",
                p.price if p.price is not None else "", p.source,
                c.purchase_price if c.purchase_price is not None else "",
            ])


def price_summary(priced: list[PricedCard]) -> str:
    ok = [p for p in priced if p.ok]
    total = sum((p.price * p.card.quantity for p in ok), Decimal("0"))
    fallback = [p for p in ok if p.source != "avg30"]
    failed = [p for p in priced if not p.ok]
    lines = [f"{len(ok)}/{len(priced)} lignes avec un prix, valeur totale {total} €"]
    if fallback:
        lines.append(f"{len(fallback)} ligne(s) au prix trend faute de moyenne 30 jours")
    if failed:
        lines.append(f"{len(failed)} ligne(s) sans prix, à vérifier :")
        lines.extend(f"  - {p.card.name} ({p.card.set_code} {p.card.collector_number}) : {p.source}" for p in failed)
    return "\n".join(lines)
