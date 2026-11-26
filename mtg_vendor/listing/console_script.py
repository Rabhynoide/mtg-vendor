"""Script à coller dans la console du navigateur, sur la page « Lister les cartes en masse ».

Tu ouvres la page toi-même dans ton navigateur habituel (et tu passes donc toi-même la vérification
Cloudflare). Le script remplit les lignes de tes cartes ; tu vérifies et tu cliques sur
« Mettre des cartes en vente ». Rien n'est envoyé par le script.

Les cartes déjà soumises sont mémorisées dans le navigateur (localStorage de cardmarket.com) :
relancer le script sur la même page remplit les variantes restantes (ex. la version foil d'une carte
déjà mise en vente en non foil) sans refaire les autres.
"""

from __future__ import annotations

import json

from ..pricing import PricedCard
from .bulk_form import CONDITION_IDS, LANGUAGE_IDS, MAX_AMOUNT

TEMPLATE = r"""// mtg-vendor : remplissage de « Lister les cartes en masse » — __LABEL__
(() => {
  const ITEMS = __ITEMS__;
  const STORE = "mtg-vendor-done";
  const done = new Set(JSON.parse(localStorage.getItem(STORE) || "[]"));
  const form = document.getElementById("BulkListingForm");
  if (!form) { alert("mtg-vendor : ouvre d'abord la page « Lister les cartes en masse » de l'édition __LABEL__."); return; }

  const rows = {};
  form.querySelectorAll('input[name^="idProduct["]').forEach(el => {
    const n = el.name.slice(10, -1);
    if (!(el.value in rows)) rows[el.value] = n;
  });

  const set = (sel, value, isCheck) => {
    const el = form.querySelector(sel);
    if (!el) return;
    if (isCheck) el.checked = value; else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const filled = [], waiting = [];
  for (const it of ITEMS) {
    if (done.has(it.key)) continue;
    const n = rows[it.p];
    if (n === undefined) { waiting.push(it); continue; }
    delete rows[it.p];  // une seule variante par ligne et par passage
    set(`select[name="idLanguage[${n}]"]`, String(it.l));
    set(`select[name="idCondition[${n}]"]`, String(it.c));
    set(`input[name="isFoil[${n}]"]`, it.f, true);
    set(`input[name="amount[${n}]"]`, String(it.a));
    set(`input[name="price[${n}]"]`, it.pr);
    const tr = form.querySelector(`input[name="idProduct[${n}]"]`).closest("tr");
    if (tr) tr.style.outline = "2px solid #f5a623";
    filled.push(it);
  }

  window.__mtgVendorPending = filled.map(it => it.key);
  if (!form.dataset.mtgVendor) {
    form.dataset.mtgVendor = "1";
    form.addEventListener("submit", () => {
      const s = new Set(JSON.parse(localStorage.getItem(STORE) || "[]"));
      (window.__mtgVendorPending || []).forEach(k => s.add(k));
      localStorage.setItem(STORE, JSON.stringify([...s]));
      window.__mtgVendorPending = [];
    }, true);
  }

  const remaining = ITEMS.filter(it => !done.has(it.key) && !filled.includes(it));
  console.table(filled.map(it => ({ carte: it.n, quantite: it.a, prix: it.pr, foil: it.f })));
  const msg = `mtg-vendor : ${filled.length} ligne(s) remplie(s) (encadrées en orange).\n` +
    (remaining.length ? `${remaining.length} carte(s) restante(s) : page suivante, ou relance le script ici après validation (autres variantes).\n` : "Toutes les cartes de cette édition sont remplies.\n") +
    "Vérifie, puis clique sur « Mettre des cartes en vente ».";
  console.log(msg);
  return { remplies: filled.length, restantes: remaining.length };
})();
"""


def item_key(p: PricedCard) -> str:
    c = p.card
    return f"{p.id_product}|{c.language}|{c.condition}|{'f' if c.foil else 'n'}|{c.collector_number}"


def build_script(label: str, items: list[PricedCard]) -> str:
    data = []
    for p in items:
        c = p.card
        remaining = c.quantity
        part = 0
        while remaining > 0:  # le champ « Nombre » est limité à 32
            amount = min(remaining, MAX_AMOUNT)
            data.append({
                "key": item_key(p) + (f"#{part}" if part else ""),
                "p": str(p.id_product),
                "l": LANGUAGE_IDS[c.language],
                "c": CONDITION_IDS[c.condition],
                "f": c.foil,
                "a": amount,
                "pr": f"{p.price:.2f}",
                "n": c.name,
            })
            remaining -= amount
            part += 1
    return TEMPLATE.replace("__LABEL__", label).replace("__ITEMS__", json.dumps(data, ensure_ascii=False))
