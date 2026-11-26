"""Point d'entrée en ligne de commande."""

from __future__ import annotations

import argparse
import sys

from .moxfield import MoxfieldFormatError, read_export, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mtg-vendor")
    sub = parser.add_subparsers(dest="command", required=True)
    p_read = sub.add_parser("lire", help="Lire un export CSV Moxfield et afficher un résumé")
    p_read.add_argument("csv", help="Chemin de l'export Moxfield (haves)")
    args = parser.parse_args(argv)

    if args.command == "lire":
        try:
            result = read_export(args.csv)
        except (OSError, MoxfieldFormatError) as exc:
            print(f"Erreur : {exc}", file=sys.stderr)
            return 1
        print(summary(result))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
