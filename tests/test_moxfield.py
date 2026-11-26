from decimal import Decimal
from pathlib import Path

import pytest

from mtg_vendor.cli import main
from mtg_vendor.moxfield import MoxfieldFormatError, read_export

SAMPLE = Path(__file__).parent / "fixtures" / "moxfield_sample.csv"


def test_reads_valid_cards():
    result = read_export(SAMPLE)
    names = [c.name for c in result.cards]
    assert names == [
        "Barkchannel Pathway // Tidechannel Pathway",
        "Diabolic Intent",
        "Old-Growth Troll",
        "Wake of Destruction",
        "Etched Card",
    ]
    assert result.total_quantity == 6


def test_fields_are_mapped_to_cardmarket():
    cards = {c.name: c for c in read_export(SAMPLE).cards}
    pathway = cards["Barkchannel Pathway // Tidechannel Pathway"]
    assert (pathway.set_code, pathway.collector_number) == ("khm", "251")
    assert (pathway.condition, pathway.language, pathway.foil) == ("NM", "French", True)
    assert pathway.purchase_price == Decimal("5.03")

    assert cards["Diabolic Intent"].condition == "MT"
    assert cards["Diabolic Intent"].quantity == 2
    assert cards["Old-Growth Troll"].collector_number == "185p"
    assert cards["Wake of Destruction"].purchase_price is None

    etched = cards["Etched Card"]
    assert (etched.foil, etched.etched, etched.altered) == (True, True, True)
    assert (etched.condition, etched.language) == ("PL", "German")
    assert etched.purchase_price is None


def test_invalid_rows_and_proxies_are_reported():
    errors = read_export(SAMPLE).errors
    assert len(errors) == 2
    assert "Some Proxy" in errors[0] and "proxy" in errors[0]
    assert "ligne 7" in errors[1] and "Like New" in errors[1]


def test_groups_by_set():
    groups = read_export(SAMPLE).by_set()
    assert list(groups) == ["bro", "khm", "pkhm", "plst"]
    assert len(groups["khm"]) == 2


def test_rejects_non_moxfield_file(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n")
    with pytest.raises(MoxfieldFormatError):
        read_export(bad)


def test_cli_summary(capsys):
    assert main(["lire", str(SAMPLE)]) == 0
    out = capsys.readouterr().out
    assert "5 lignes, 6 cartes, 4 éditions" in out
    assert "2 ligne(s) à vérifier" in out
