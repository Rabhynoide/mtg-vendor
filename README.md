# mtg-vendor

Mettre en vente sur Cardmarket une collection Magic exportée depuis Moxfield.

## Installation

```
pip install -e .[dev]
```

## Utilisation

1. Sur Moxfield, exporte ta collection en CSV (« haves »).
2. `mtg-vendor lire export.csv` : résumé de l'export (cartes, états, langues, éditions, lignes à vérifier).
3. `mtg-vendor prix export.csv -o prix.csv` : associe chaque carte à son produit Cardmarket
   (via l'identifiant `cardmarket_id` de Scryfall) et calcule son prix de vente :
   moyenne des ventes sur 30 jours (`avg30`, ou `avg30-foil` pour une foil) du guide des prix public de Cardmarket,
   prix « trend » à défaut, 0,02 € minimum. Les cartes sans prix sont listées à la fin.

Les fichiers Cardmarket sont gardés en cache 20 h dans `~/.cache/mtg-vendor` (modifiable avec `MTG_VENDOR_CACHE`).

Conception : [docs/etape1-mise-en-vente.md](docs/etape1-mise-en-vente.md).
