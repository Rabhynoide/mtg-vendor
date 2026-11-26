"""Découpage des cartes à vendre en lots pour le formulaire « Lister les cartes en masse »."""

from __future__ import annotations

from dataclasses import dataclass

from .pricing import PricedCard

MAX_ROWS_PER_BATCH = 100  # limite du formulaire Cardmarket


@dataclass(frozen=True)
class Batch:
    id_expansion: int
    set_code: str
    items: tuple[PricedCard, ...]

    @property
    def quantity(self) -> int:
        return sum(p.card.quantity for p in self.items)


def make_batches(priced: list[PricedCard], max_rows: int = MAX_ROWS_PER_BATCH) -> list[Batch]:
    """Regroupe par édition Cardmarket (une page du formulaire), puis découpe en lots de max_rows lignes.

    Les cartes sans prix ou sans édition Cardmarket sont ignorées : elles sont déjà signalées par `prix`.
    """
    groups: dict[int, list[PricedCard]] = {}
    for p in priced:
        if p.ok and p.id_expansion is not None:
            groups.setdefault(p.id_expansion, []).append(p)

    batches = []
    for id_expansion, items in sorted(groups.items(), key=lambda kv: kv[1][0].card.set_code):
        items.sort(key=lambda p: (p.card.collector_number.zfill(6), p.card.foil))
        for i in range(0, len(items), max_rows):
            batches.append(Batch(id_expansion, items[0].card.set_code, tuple(items[i : i + max_rows])))
    return batches
