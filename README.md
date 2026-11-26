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

4. `mtg-vendor vendre export.csv` : ouvre un navigateur, va sur « Lister les cartes en masse » édition par édition,
   et remplit langue, état, foil, quantité et prix de tes cartes. **L'appli ne valide jamais elle-même** :
   tu vérifies la page, tu cliques sur « Mettre des cartes en vente », puis tu appuies sur Entrée dans le terminal.
   - Première fois : `py -m pip install -e .[vente]` puis `py -m playwright install chromium`,
     et connecte-toi à Cardmarket dans la fenêtre qui s'ouvre (la session est gardée dans `~/.mtg-vendor/navigateur`).
   - `--edition khm` pour ne traiter qu'une édition (répétable), `--canal chrome` pour utiliser ton Chrome installé.
   - Les cartes mises en vente sont notées dans `mises_en_vente.json` : relancer la commande ne crée pas de doublons.
   - Les cartes altérées et celles sans prix sont ignorées.

Les fichiers Cardmarket sont gardés en cache 20 h dans `~/.cache/mtg-vendor` (modifiable avec `MTG_VENDOR_CACHE`).

Conception : [docs/etape1-mise-en-vente.md](docs/etape1-mise-en-vente.md).
