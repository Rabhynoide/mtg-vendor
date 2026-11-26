"""Remplissage du formulaire Cardmarket « Lister les cartes en masse » avec Playwright.

Principe :
- un navigateur visible, avec un profil dédié où tu te connectes toi-même à Cardmarket (aucun mot de passe stocké) ;
- une page par édition (`idExpansion`), 100 cartes par page (`site=2`, `site=3`…) ;
- chaque ligne du tableau porte un champ caché `idProduct[N]` : on remplit les lignes de nos cartes ;
- l'appli ne clique JAMAIS sur « Mettre des cartes en vente » : tu vérifies et tu cliques, puis tu confirmes dans le terminal.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Iterable

from ..pricing import PricedCard

BASE_URL = "https://www.cardmarket.com/fr/Magic/Stock/ListingMethods/BulkListing"
PROFILE_DIR = Path.home() / ".mtg-vendor" / "navigateur"
MAX_AMOUNT = 32  # maximum accepté par le champ « Nombre »

LANGUAGE_IDS = {
    "English": 1, "French": 2, "German": 3, "Spanish": 4, "Italian": 5, "S-Chinese": 6,
    "Japanese": 7, "Portuguese": 8, "Russian": 9, "Korean": 10, "T-Chinese": 11,
}
CONDITION_IDS = {"MT": 1, "NM": 2, "EX": 3, "GD": 4, "LP": 5, "PL": 6, "PO": 7}


def page_url(id_expansion: int, site: int, base_url: str = BASE_URL) -> str:
    url = f"{base_url}?idExpansion={id_expansion}&sortBy=number"
    return url if site == 1 else f"{url}&site={site}"


@dataclass(frozen=True)
class Assignment:
    row: int
    item: PricedCard
    amount: int


def plan_page(rows: list[tuple[int, int]], pending: Iterable[PricedCard]) -> list[Assignment]:
    """Associe les cartes en attente aux lignes de la page (idProduct identique).

    Une ligne ne reçoit qu'une carte. Si une même carte existe en plusieurs variantes (foil, état…),
    les suivantes attendent le passage suivant sur la même page.
    """
    free = {}
    for row, id_product in rows:
        free.setdefault(id_product, row)
    out = []
    for item in pending:
        row = free.pop(item.id_product, None)
        if row is not None:
            out.append(Assignment(row, item, min(item.card.quantity, MAX_AMOUNT)))
    return out


def _pause(slow: bool) -> None:
    if slow:
        time.sleep(random.uniform(0.15, 0.4))


def read_rows(page) -> list[tuple[int, int]]:
    """Renvoie [(N, idProduct)] pour chaque ligne du tableau."""
    values = page.eval_on_selector_all(
        '#BulkListingForm input[name^="idProduct["]',
        "els => els.map(e => [e.name, e.value])",
    )
    rows = []
    for name, value in values:
        rows.append((int(name[len("idProduct["):-1]), int(value)))
    return rows


def has_next_page(page) -> bool:
    return page.locator('a.pagination-control[data-direction="next"]:not(.disabled)').count() > 0


def fill_row(page, a: Assignment, slow: bool = True) -> None:
    card, n = a.item.card, a.row
    page.select_option(f'select[name="idLanguage[{n}]"]', str(LANGUAGE_IDS[card.language]))
    _pause(slow)
    page.select_option(f'select[name="idCondition[{n}]"]', str(CONDITION_IDS[card.condition]))
    _pause(slow)
    page.set_checked(f'input[name="isFoil[{n}]"]', card.foil)
    page.fill(f'input[name="amount[{n}]"]', str(a.amount))
    _pause(slow)
    page.fill(f'input[name="price[{n}]"]', f"{a.item.price:.2f}")
    _pause(slow)


def is_listing_page(page) -> bool:
    return page.locator("#BulkListingForm").count() > 0


def describe(assignments: list[Assignment]) -> str:
    lines = []
    for a in assignments:
        c = a.item.card
        foil = " foil" if c.foil else ""
        lines.append(f"  {a.amount} x {c.name} ({c.set_code} {c.collector_number}) {c.language} {c.condition}{foil} : {a.item.price} €")
    return "\n".join(lines)


def list_expansion(
    page,
    id_expansion: int,
    items: list[PricedCard],
    confirm: Callable[[str], bool],
    on_listed: Callable[[list[PricedCard]], None],
    wait_login: Callable[[], None],
    base_url: str = BASE_URL,
    slow: bool = True,
    log: Callable[[str], None] = print,
) -> list[PricedCard]:
    """Met en vente les cartes d'une édition. Renvoie les cartes qui n'ont pas été mises en vente."""
    pending = list(items)
    not_done: list[PricedCard] = []
    site = 1
    while pending:
        page.goto(page_url(id_expansion, site, base_url))
        if not is_listing_page(page):
            wait_login()
            page.goto(page_url(id_expansion, site, base_url))
            if not is_listing_page(page):
                raise RuntimeError("La page « Lister les cartes en masse » ne s'affiche pas (connexion ?).")

        assignments = plan_page(read_rows(page), pending)
        if not assignments:
            if has_next_page(page):
                site += 1
                continue
            log(f"{len(pending)} carte(s) introuvable(s) dans le formulaire de cette édition.")
            not_done.extend(pending)
            break

        for a in assignments:
            fill_row(page, a, slow)
        summary = describe(assignments)
        log(f"Page {site} remplie ({len(assignments)} ligne(s)) :\n{summary}")

        placed = {id(a.item): a for a in assignments}
        listed = [replace(a.item, card=replace(a.item.card, quantity=a.amount)) for a in assignments]
        ok = confirm(summary)
        if ok:
            on_listed(listed)
        next_pending = []
        for item in pending:
            a = placed.get(id(item))
            if a is None:
                next_pending.append(item)
            elif not ok:
                not_done.append(item)
            elif item.card.quantity > a.amount:
                next_pending.append(replace(item, card=replace(item.card, quantity=item.card.quantity - a.amount)))
        pending = next_pending
        # On recharge la même page : il peut rester d'autres variantes des mêmes cartes.
    return not_done


BRAVE_PATHS = [
    Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path.home() / "AppData/Local/BraveSoftware/Brave-Browser/Application/brave.exe",
    Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
    Path("/usr/bin/brave-browser"),
]


def find_brave() -> str | None:
    for path in BRAVE_PATHS:
        if path.exists():
            return str(path)
    return None


def open_browser(playwright, channel: str | None = None, profile_dir: Path = PROFILE_DIR):
    """channel : None (Chromium de Playwright), "chrome", "msedge", "brave" ou le chemin d'un exécutable."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    options = {}
    if channel == "brave":
        exe = find_brave()
        if exe is None:
            raise RuntimeError("Brave introuvable : passe le chemin de brave.exe à --canal")
        options["executable_path"] = exe
    elif channel and (channel.endswith(".exe") or "/" in channel or "\\" in channel):
        options["executable_path"] = channel
    elif channel:
        options["channel"] = channel
    context = playwright.chromium.launch_persistent_context(
        str(profile_dir), headless=False, locale="fr-FR", viewport={"width": 1400, "height": 900}, **options,
    )
    page = context.pages[0] if context.pages else context.new_page()
    return context, page
