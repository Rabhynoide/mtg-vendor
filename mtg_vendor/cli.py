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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
