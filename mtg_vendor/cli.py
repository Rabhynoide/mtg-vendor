"""Point d'entrée en ligne de commande."""

from __future__ import annotations

import argparse
import sys
import urllib.error

from .moxfield import MoxfieldFormatError, read_export, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mtg-vendor")
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("lire", help="Lire un export CSV Moxfield et afficher un résumé")
    p_read.add_argument("csv", help="Chemin de l'export Moxfield (haves)")

    p_price = sub.add_parser("prix", help="Associer les cartes à Cardmarket et calculer le prix (moyenne 30 jours)")
    p_price.add_argument("csv", help="Chemin de l'export Moxfield (haves)")
    p_price.add_argument("-o", "--sortie", default="prix.csv", help="Fichier CSV du rapport (défaut : prix.csv)")

    p_sell = sub.add_parser("vendre", help="Remplir le formulaire Cardmarket « Lister les cartes en masse »")
    p_sell.add_argument("csv", help="Chemin de l'export Moxfield (haves)")
    p_sell.add_argument("--edition", action="append", help="Code d'édition Moxfield à traiter (ex. khm), répétable")
    p_sell.add_argument("--suivi", default="mises_en_vente.json", help="Fichier de suivi des cartes déjà en vente")
    p_sell.add_argument("--canal", default=None, help="Navigateur installé à utiliser : brave, chrome, msedge, ou le chemin d'un exécutable (défaut : Chromium de Playwright)")

    args = parser.parse_args(argv)

    try:
        result = read_export(args.csv)
    except (OSError, MoxfieldFormatError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    if args.command == "lire":
        print(summary(result))
        return 0

    if args.command == "prix":
        from .cardmarket_data import CardmarketCatalog
        from .pricing import price_all, price_summary, write_report
        from .scryfall import resolve_cardmarket_ids

        try:
            catalog = CardmarketCatalog.load()
            ids = resolve_cardmarket_ids((c.set_code, c.collector_number) for c in result.cards)
        except urllib.error.URLError as exc:
            print(f"Erreur réseau : {exc}", file=sys.stderr)
            return 1
        priced = price_all(result.cards, ids, catalog)
        write_report(priced, args.sortie)
        print(price_summary(priced))
        print(f"Rapport écrit dans {args.sortie}")
        return 0

    if args.command == "vendre":
        return sell(result.cards, args)
    return 2


def sell(cards, args) -> int:
    from .batches import make_batches
    from .cardmarket_data import CardmarketCatalog
    from .pricing import price_all
    from .scryfall import resolve_cardmarket_ids
    from .state import ListingLedger

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright n'est pas installé : py -m pip install -e .[vente] puis py -m playwright install chromium",
              file=sys.stderr)
        return 1
    from .listing.bulk_form import list_expansion, open_browser

    if args.edition:
        wanted = {e.lower() for e in args.edition}
        cards = [c for c in cards if c.set_code in wanted]
    altered = [c for c in cards if c.altered]
    if altered:
        print(f"{len(altered)} carte(s) altérée(s) ignorée(s) : le formulaire n'a pas de case « altérée ».")
    cards = [c for c in cards if not c.altered]

    try:
        catalog = CardmarketCatalog.load()
        ids = resolve_cardmarket_ids((c.set_code, c.collector_number) for c in cards)
    except urllib.error.URLError as exc:
        print(f"Erreur réseau : {exc}", file=sys.stderr)
        return 1

    ledger = ListingLedger(args.suivi)
    priced = ledger.remaining(price_all(cards, ids, catalog))
    unpriced = [p for p in priced if not p.ok]
    if unpriced:
        print(f"{len(unpriced)} carte(s) sans prix ignorée(s) (voir « mtg-vendor prix »).")
    groups = {}
    for batch in make_batches(priced):
        groups.setdefault((batch.id_expansion, batch.set_code), []).extend(batch.items)
    if not groups:
        print("Rien à mettre en vente : tout est déjà dans le fichier de suivi.")
        return 0
    total = sum(p.card.quantity for items in groups.values() for p in items)
    print(f"{total} carte(s) à mettre en vente sur {len(groups)} édition(s).")

    def wait_login():
        input("Connecte-toi à Cardmarket dans la fenêtre du navigateur, puis appuie sur Entrée ici… ")

    def confirm(summary):
        answer = input(
            "Vérifie la page, corrige si besoin, puis clique sur « Mettre des cartes en vente ».\n"
            "Appuie sur Entrée une fois la mise en vente réussie, ou tape « n » pour ne pas l'enregistrer : "
        )
        return answer.strip().lower() not in {"n", "non"}

    not_done = []
    with sync_playwright() as p:
        context, page = open_browser(p, channel=args.canal)
        try:
            for (id_expansion, set_code), items in groups.items():
                print(f"\n=== {set_code} : {sum(i.card.quantity for i in items)} carte(s) ===")
                not_done += list_expansion(page, id_expansion, items, confirm, ledger.record, wait_login)
        finally:
            context.close()
    if not_done:
        print(f"\n{len(not_done)} carte(s) non mises en vente :")
        for p in not_done:
            print(f"  - {p.card.name} ({p.card.set_code} {p.card.collector_number})")
    print(f"Suivi enregistré dans {args.suivi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
