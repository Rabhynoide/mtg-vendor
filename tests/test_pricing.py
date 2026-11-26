import csv
from decimal import Decimal
from pathlib import Path

import pytest

from mtg_vendor import cache
from mtg_vendor.cardmarket_data import PRICE_GUIDE_URL, PRODUCTS_URL, CardmarketCatalog
from mtg_vendor.moxfield import read_export
from mtg_vendor.pricing import price_all, price_summary, write_report
from mtg_vendor.scryfall import COLLECTION_URL, resolve_cardmarket_ids

SAMPLE = Path(__file__).parent / "fixtures" / "moxfield_sample.csv"

PRODUCTS = {"version": 1, "products": [
    {"idProduct": 100, "name": "Barkchannel Pathway // Tidechannel Pathway", "idCategory": 1,
     "categoryName": "Magic Single", "idExpansion": 3061, "idMetacard": 1, "dateAdded": "2021-01-01 00:00:00"},
    {"idProduct": 200, "name": "Diabolic Intent", "idCategory": 1,
     "categoryName": "Magic Single", "idExpansion": 4651, "idMetacard": 2, "dateAdded": "2022-01-01 00:00:00"},
    {"idProduct": 300, "name": "Old-Growth Troll", "idCategory": 1,
     "categoryName": "Magic Single", "idExpansion": 3070, "idMetacard": 3, "dateAdded": "2021-01-01 00:00:00"},
]}
PRICES = {"version": 1, "priceGuides": [
    {"idProduct": 100, "avg30": 3.0, "trend": 3.1, "avg30-foil": 6.456, "trend-foil": 6.0},
    {"idProduct": 200, "avg30": 12.5, "trend": 12.0, "avg30-foil": None, "trend-foil": None},
    {"idProduct": 300, "avg30": None, "trend": 0.01, "avg30-foil": None, "trend-foil": None},
]}
SCRYFALL = {
    ("khm", "251"): 100, ("bro", "89"): 200, ("pkhm", "185p"): 300,
    ("plst", "UDS-99"): None, ("khm", "3"): None,
}


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("MTG_VENDOR_CACHE", str(tmp_path / "cache"))


def fake_post(url, payload):
    assert url == COLLECTION_URL
    data = []
    for ident in payload["identifiers"]:
        cm = SCRYFALL.get((ident["set"], ident["collector_number"]))
        if cm is not None:
            data.append({"set": ident["set"], "collector_number": ident["collector_number"], "cardmarket_id": cm})
    return {"data": data, "not_found": []}


def fake_get(url):
    return {PRODUCTS_URL: PRODUCTS, PRICE_GUIDE_URL: PRICES}[url]


def priced_sample():
    cards = read_export(SAMPLE).cards
    ids = resolve_cardmarket_ids(((c.set_code, c.collector_number) for c in cards), post_json=fake_post, pause=lambda: None)
    catalog = CardmarketCatalog.load(get_json=fake_get)
    return {p.card.name: p for p in price_all(cards, ids, catalog)}


def test_uses_avg30_and_foil_price():
    priced = priced_sample()
    pathway = priced["Barkchannel Pathway // Tidechannel Pathway"]  # foil
    assert (pathway.price, pathway.source, pathway.id_expansion) == (Decimal("6.46"), "avg30", 3061)
    assert priced["Diabolic Intent"].price == Decimal("12.50")


def test_falls_back_to_trend_with_minimum_price():
    troll = priced_sample()["Old-Growth Troll"]
    assert troll.price == Decimal("0.02")
    assert troll.source.startswith("trend")


def test_unmatched_cards_have_no_price():
    priced = priced_sample()
    assert priced["Wake of Destruction"].price is None
    assert "introuvable" in priced["Wake of Destruction"].source


def test_scryfall_batches_and_cache():
    calls = []

    def counting_post(url, payload):
        calls.append(len(payload["identifiers"]))
        return fake_post(url, payload)

    printings = [("khm", "251")] + [("xxx", str(i)) for i in range(100)]
    resolve_cardmarket_ids(printings, post_json=counting_post, pause=lambda: None)
    assert calls == [75, 26]
    assert cache.load_json("scryfall_ids.json", {}) == {"khm/251": 100}

    calls.clear()
    ids = resolve_cardmarket_ids([("khm", "251")], post_json=counting_post, pause=lambda: None)
    assert calls == [] and ids[("khm", "251")] == 100


def test_report_and_summary(tmp_path):
    priced = list(priced_sample().values())
    out = tmp_path / "prix.csv"
    write_report(priced, out)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 5
    assert rows[0]["Prix"] == "6.46" and rows[0]["idProduct"] == "100"
    text = price_summary(priced)
    assert "3/5 lignes avec un prix" in text
    assert "valeur totale 31.48 €" in text  # 6.46 + 2 x 12.50 + 0.02
