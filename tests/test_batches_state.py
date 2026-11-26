from dataclasses import replace
from decimal import Decimal

from mtg_vendor.batches import make_batches
from mtg_vendor.moxfield import Card
from mtg_vendor.pricing import PricedCard
from mtg_vendor.state import ListingLedger


def pc(name, set_code, number, id_exp, qty=1, foil=False, price="1.00"):
    card = Card(name, set_code, number, qty, "NM", "French", foil, False, False, False, None, 2)
    return PricedCard(card, 1, id_exp, name, Decimal(price) if price else None, "avg30")


def test_batches_group_by_expansion_and_split():
    priced = [pc(f"K{i}", "khm", str(i), 3660) for i in range(150)] + [pc("B", "bro", "5", 5164)]
    priced.append(pc("NoPrice", "khm", "999", 3660, price=None))
    batches = make_batches(priced)
    assert [(b.set_code, len(b.items)) for b in batches] == [("bro", 1), ("khm", 100), ("khm", 50)]
    assert batches[1].items[0].card.collector_number == "0"
    assert batches[1].items[1].card.collector_number == "1"  # tri numérique, pas alphabétique


def test_ledger_skips_already_listed(tmp_path):
    path = tmp_path / "ledger.json"
    a, b = pc("A", "khm", "1", 3660, qty=2), pc("B", "khm", "2", 3660)
    ledger = ListingLedger(path)
    ledger.record([replace(a, card=replace(a.card, quantity=1)), b])

    reloaded = ListingLedger(path)
    remaining = reloaded.remaining([a, b])
    assert [(p.card.name, p.card.quantity) for p in remaining] == [("A", 1)]


def test_ledger_distinguishes_foil(tmp_path):
    ledger = ListingLedger(tmp_path / "l.json")
    ledger.record([pc("A", "khm", "1", 3660)])
    assert len(ledger.remaining([pc("A", "khm", "1", 3660, foil=True)])) == 1
