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

4. `mtg-vendor script export.csv` (**méthode recommandée**) : écrit dans `scripts/` un script par édition et
   un `LISEZMOI.txt` avec l'adresse de la page Cardmarket de chaque édition. Pour chaque édition :
   ouvre l'adresse dans ton navigateur habituel (connecté), F12 > Console, colle le contenu de `scripts/<édition>.js`, Entrée.
   Le script remplit langue, état, foil, quantité et prix de tes cartes et les encadre en orange ;
   tu vérifies et tu cliques sur « Mettre des cartes en vente ». Il ne soumet rien lui-même.
   - Édition sur plusieurs pages : relance le script sur chaque page (`site=2`, `site=3`…).
   - Même carte en plusieurs variantes (foil et non foil…) : après validation, recharge la page et relance le script.
     Les cartes déjà soumises sont mémorisées dans le navigateur et ne sont pas refaites.
   - La première fois, Brave/Chrome demande de taper `allow pasting` dans la console avant de coller.
5. `mtg-vendor vendre export.csv` (expérimental) : même chose avec un navigateur piloté par Playwright.
   **Cloudflare bloque actuellement ce navigateur sur Cardmarket** : utilise plutôt `script`.
   Détails : : ouvre un navigateur, va sur « Lister les cartes en masse » édition par édition,
   et remplit langue, état, foil, quantité et prix de tes cartes. **L'appli ne valide jamais elle-même** :
   tu vérifies la page, tu cliques sur « Mettre des cartes en vente », puis tu appuies sur Entrée dans le terminal.
   - Première fois : `py -m pip install -e .[vente]` puis `py -m playwright install chromium`,
     et connecte-toi à Cardmarket dans la fenêtre qui s'ouvre (la session est gardée dans `~/.mtg-vendor/navigateur`).
   - `--edition khm` pour ne traiter qu'une édition (répétable), `--canal brave` (ou `chrome`, `msedge`, ou le chemin d'un exécutable) pour utiliser un navigateur installé.
   - Les cartes mises en vente sont notées dans `mises_en_vente.json` : relancer la commande ne crée pas de doublons.
   - Les cartes altérées et celles sans prix sont ignorées.

Les fichiers Cardmarket sont gardés en cache 20 h dans `~/.cache/mtg-vendor` (modifiable avec `MTG_VENDOR_CACHE`).

Conception : [docs/etape1-mise-en-vente.md](docs/etape1-mise-en-vente.md).
