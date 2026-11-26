import json
import os
from decimal import Decimal
from pathlib import Path

import pytest

from mtg_vendor.listing.console_script import build_script
from mtg_vendor.moxfield import Card
from mtg_vendor.pricing import PricedCard

FIXTURE = (Path(__file__).parent / "fixtures" / "bulk_listing.html").read_text().replace("NEXTCLASS", "")


def pc(name, id_product, qty=1, foil=False, cond="NM", lang="French", price="1.50"):
    card = Card(name, "khm", "1", qty, cond, lang, foil, False, False, False, None, 2)
    return PricedCard(card, id_product, 3660, name, Decimal(price), "avg30")


def test_splits_quantity_over_32():
    script = build_script("khm", [pc("Big", 111, qty=40)])
    data = json.loads(script.split("const ITEMS = ", 1)[1].split(";\n", 1)[0])
    assert [d["a"] for d in data] == [32, 8]
    assert data[0]["key"] != data[1]["key"]


@pytest.fixture
def page():
    sync_api = pytest.importorskip("playwright.sync_api")
    exe = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(executable_path=exe if os.path.exists(exe) else None)
        except Exception as exc:
            pytest.skip(f"Chromium indisponible : {exc}")
        pg = browser.new_page()
        pg.route("https://cm.test/**", lambda r: r.fulfill(content_type="text/html", body=FIXTURE))
        pg.goto("https://cm.test/page")
        yield pg
        browser.close()


def test_script_fills_rows_and_remembers_submitted(page):
    script = build_script("khm", [
        pc("A", 111, qty=2, cond="MT"), pc("A foil", 111, foil=True, lang="German", price="3.00"), pc("Elsewhere", 999),
    ])
    page.on("dialog", lambda d: d.dismiss())
    result = page.evaluate(script)
    assert result == {"remplies": 1, "restantes": 2}
    assert page.input_value('select[name="idLanguage[0]"]') == "2"
    assert page.input_value('select[name="idCondition[0]"]') == "1"
    assert page.input_value('input[name="amount[0]"]') == "2"
    assert page.input_value('input[name="price[0]"]') == "1.50"
    assert page.input_value('input[name="amount[1]"]') == "0"

    # L'utilisateur valide : on simule l'envoi sans quitter la page.
    page.evaluate("""() => { const f = document.getElementById('BulkListingForm');
        f.addEventListener('submit', e => e.preventDefault()); f.requestSubmit(); }""")
    page.reload()
    result = page.evaluate(script)
    assert result == {"remplies": 1, "restantes": 1}
    assert page.is_checked('input[name="isFoil[0]"]')
    assert page.input_value('select[name="idLanguage[0]"]') == "3"
    assert page.input_value('input[name="price[0]"]') == "3.00"


def test_cli_script_writes_one_file_per_edition(tmp_path, monkeypatch, capsys):
    from mtg_vendor import cardmarket_data, cli, scryfall
    from tests.test_pricing import PRODUCTS, PRICES, fake_post

    monkeypatch.setenv("MTG_VENDOR_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(cardmarket_data.http, "get_json",
                        lambda url: {cardmarket_data.PRODUCTS_URL: PRODUCTS, cardmarket_data.PRICE_GUIDE_URL: PRICES}[url])
    monkeypatch.setattr(scryfall.http, "post_json", fake_post)
    sample = Path(__file__).parent / "fixtures" / "moxfield_sample.csv"
    assert cli.main(["script", str(sample), "-o", str(tmp_path / "out")]) == 0
    files = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert files == ["LISEZMOI.txt", "bro.js", "khm.js", "pkhm.js"]
    readme = (tmp_path / "out" / "LISEZMOI.txt").read_text(encoding="utf-8")
    assert "idExpansion=3061" in readme
