"""Lecture de l'export CSV « haves » de Moxfield."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED_COLUMNS = {"Count", "Name", "Edition", "Condition", "Language", "Foil", "Collector Number"}

# Moxfield -> grades Cardmarket (MT, NM, EX, GD, LP, PL, PO).
# Moxfield n'a pas d'équivalent exact pour tous les grades : on choisit le plus prudent.
CONDITIONS = {
    "mint": "MT",
    "near mint": "NM",
    "lightly played": "EX",
    "good (lightly played)": "EX",
    "played": "GD",
    "moderately played": "GD",
    "heavily played": "PL",
    "damaged": "PO",
}

# Moxfield -> libellé de langue Cardmarket.
LANGUAGES = {
    "english": "English",
    "french": "French",
    "german": "German",
    "spanish": "Spanish",
    "italian": "Italian",
    "portuguese": "Portuguese",
    "japanese": "Japanese",
    "korean": "Korean",
    "russian": "Russian",
    "chinese simplified": "S-Chinese",
    "simplified chinese": "S-Chinese",
    "chinese traditional": "T-Chinese",
    "traditional chinese": "T-Chinese",
}


class MoxfieldFormatError(ValueError):
    """Le fichier ne ressemble pas à un export Moxfield."""


@dataclass(frozen=True)
class Card:
    name: str
    set_code: str
    collector_number: str
    quantity: int
    condition: str  # grade Cardmarket
    language: str  # libellé Cardmarket
    foil: bool
    etched: bool
    altered: bool
    proxy: bool
    purchase_price: Decimal | None
    line: int  # numéro de ligne dans le CSV, pour les messages d'erreur


@dataclass
class ParseResult:
    cards: list[Card]
    errors: list[str]

    @property
    def total_quantity(self) -> int:
        return sum(c.quantity for c in self.cards)

    def by_set(self) -> dict[str, list[Card]]:
        groups: dict[str, list[Card]] = {}
        for card in self.cards:
            groups.setdefault(card.set_code, []).append(card)
        return dict(sorted(groups.items()))


def _bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def _price(value: str) -> Decimal | None:
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_row(row: dict[str, str], line: int) -> Card:
    name = (row.get("Name") or "").strip()
    if not name:
        raise ValueError("nom de carte vide")

    try:
        quantity = int((row.get("Count") or "").strip())
    except ValueError:
        raise ValueError(f"quantité invalide : {row.get('Count')!r}") from None
    if quantity < 1:
        raise ValueError(f"quantité invalide : {quantity}")

    raw_condition = (row.get("Condition") or "").strip()
    condition = CONDITIONS.get(raw_condition.lower())
    if condition is None:
        raise ValueError(f"état inconnu : {raw_condition!r}")

    raw_language = (row.get("Language") or "").strip()
    language = LANGUAGES.get(raw_language.lower())
    if language is None:
        raise ValueError(f"langue inconnue : {raw_language!r}")

    finish = (row.get("Foil") or "").strip().lower()
    if finish not in {"", "foil", "etched"}:
        raise ValueError(f"finition inconnue : {finish!r}")

    return Card(
        name=name,
        set_code=(row.get("Edition") or "").strip().lower(),
        collector_number=(row.get("Collector Number") or "").strip(),
        quantity=quantity,
        condition=condition,
        language=language,
        foil=finish in {"foil", "etched"},
        etched=finish == "etched",
        altered=_bool(row.get("Alter") or ""),
        proxy=_bool(row.get("Proxy") or ""),
        purchase_price=_price(row.get("Purchase Price") or ""),
        line=line,
    )


def read_export(path: str | Path) -> ParseResult:
    """Lit un export Moxfield. Les lignes invalides sont signalées sans bloquer le reste.

    Les proxys sont écartés : ils ne peuvent pas être vendus.
    """
    cards: list[Card] = []
    errors: list[str] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise MoxfieldFormatError(f"colonnes manquantes : {', '.join(sorted(missing))}")
        for line, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue
            try:
                card = parse_row(row, line)
            except ValueError as exc:
                errors.append(f"ligne {line} ({row.get('Name', '?')}) : {exc}")
                continue
            if card.proxy:
                errors.append(f"ligne {line} ({card.name}) : proxy ignoré")
                continue
            cards.append(card)
    return ParseResult(cards=cards, errors=errors)


def summary(result: ParseResult) -> str:
    lines = [
        f"{len(result.cards)} lignes, {result.total_quantity} cartes, {len(result.by_set())} éditions",
    ]
    for label, counter in (
        ("États", Counter(c.condition for c in result.cards)),
        ("Langues", Counter(c.language for c in result.cards)),
        ("Foil", Counter("foil" if c.foil else "normal" for c in result.cards)),
    ):
        lines.append(f"{label} : " + ", ".join(f"{k} {v}" for k, v in counter.most_common()))
    lines.append("Par édition : " + ", ".join(
        f"{code} {sum(c.quantity for c in cards)}" for code, cards in result.by_set().items()
    ))
    if result.errors:
        lines.append(f"{len(result.errors)} ligne(s) à vérifier :")
        lines.extend(f"  - {e}" for e in result.errors)
    return "\n".join(lines)
