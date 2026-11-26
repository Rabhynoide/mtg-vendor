# Étape 1 : comment mettre en vente sur Cardmarket sans API

## Constats (26/11/2026)

- **API fermée** : la page d'aide officielle indique « Currently, we are not accepting applications for access to the Cardmarket API ». Pas d'accès possible pour l'instant, particulier ou pro.
- **Formulaire « List bulk items »** : Cardmarket propose une page de mise en vente en lot
  (`cardmarket.com/<langue>/Magic/Stock/ListingMethods/BulkListing`), qui accepte **jusqu'à 100 articles à la fois**.
  Une extension open source ([cardmarket-bulk-import](https://github.com/PedroPerpetua/cardmarket-bulk-import)) remplit déjà ce formulaire à partir d'un CSV, et son auteur dit avoir eu l'accord du support Cardmarket.
  Reste à confirmer que cette page est accessible à un compte particulier.
- **Import CSV « officiel »** : un blog tiers l'attribue à l'abonnement payant MKM Pro (~10 €/mois). Non confirmé par Cardmarket.
- **Automatisation** : aucune source consultée ne précise la position de Cardmarket. Prudence : rythme humain, validation manuelle.

## Conception retenue

Playwright pilote un navigateur **avec ton profil connecté** (pas de mot de passe stocké dans l'appli) et :

1. ouvre la page « List bulk items » ;
2. remplit un lot de 100 articles maximum (carte, édition, langue, état, foil, quantité, prix) ;
3. **s'arrête avant l'envoi** : tu vérifies et tu cliques toi-même sur le bouton de validation (au début, on pourra automatiser ce clic plus tard) ;
4. note les cartes envoyées dans un fichier local pour éviter les doublons.

Avantage : on remplit le même formulaire qu'un humain, en 1 envoi par lot de 100, ce qui limite fortement le nombre d'actions automatisées.

## Architecture du dépôt (proposition)

```
mtg_vendor/
  moxfield.py     # lecture de l'export CSV Moxfield (étape 2)
  matching.py     # correspondance édition/numéro Moxfield -> Cardmarket (étape 3)
  pricing.py      # règle de prix réglable (étape 3)
  listing/
    base.py       # interface commune de mise en vente
    bulk_form.py  # Playwright sur le formulaire « List bulk items » (étape 4)
  state.py        # suivi des cartes déjà mises en vente
```

## Vérifié le 26/11/2026

- La page « Lister les cartes en masse » est accessible avec un compte particulier.
- Filtres dans l'adresse : `?idExpansion=<id>&idRarity=<id>&sortBy=number`.
- Après filtrage : 100 cartes par page (ex. Kaldheim : 285 résultats, 3 pages). Chaque ligne a :
  nom FR + nom EN, rareté, Langue (liste), État (liste), foil (case étoile), altérée (case), Commentaires, Nombre, Prix (€).
- Le bouton « IMPORT CSV… » vient de l'extension cardmarket-bulk-import, pas de Cardmarket.
- **Choix final** : Playwright remplit lui-même ce tableau, la validation de chaque lot reste manuelle.

Sources : [Cardmarket API (aide officielle)](https://help.cardmarket.com/en/cardmarket-api), [cardmarket-bulk-import](https://github.com/PedroPerpetua/cardmarket-bulk-import), [Guide Cardmarket 2026 (cardpulse)](https://www.cardpulse.club/blog/cardmarket-complete-guide-2026)
