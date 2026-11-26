import os
from decimal import Decimal
from pathlib import Path

import pytest

from mtg_vendor.listing.bulk_form import Assignment, list_expansion, page_url, plan_page
from mtg_vendor.moxfield import Card
from mtg_vendor.pricing import PricedCard

FIXTURE = (Path(__file__).parent / "fixtures" / "bulk_listing.html").read_text()


def pc(name, id_product, qty=1, foil=False, cond="NM", lang="French", price="1.50"):
    card = Card(name, "khm", "1", qty, cond, lang, foil, False, False, False, None, 2)
    return PricedCard(card, id_product, 3660, name, Decimal(price), "avg30")


def test_page_url():
    assert page_url(3660, 1, "https://x/B").endswith("?idExpansion=3660&sortBy=number")
    assert page_url(3660, 2, "https://x/B").endswith("&site=2")


def test_plan_page_one_variant_per_row_and_max_amount():
    a, a_foil, b, c = pc("A", 111), pc("A foil", 111, foil=True), pc("B", 222, qty=40), pc("C", 999)
    plan = plan_page([(0, 111), (1, 222)], [a, a_foil, b, c])
    assert plan == [Assignment(0, a, 1), Assignment(1, b, 32)]


def _browser_path():
    for p in ("/opt/pw-browsers/chromium-1243/chrome-linux64/chrome",):
        if os.path.exists(p):
            return p
    return None


@pytest.fixture
def page(tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    pages = {
        1: FIXTURE.replace("NEXTCLASS", ""),
        2: FIXTURE.replace('value="111"', 'value="333"').replace('value="222"', 'value="444"').replace("NEXTCLASS", "disabled"),
    }
    for n, html in pages.items():
        (tmp_path / f"p{n}.html").write_text(html)
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(executable_path=_browser_path())
        except Exception as exc:  # navigateur Playwright non installé
            pytest.skip(f"Chromium indisponible : {exc}")
        pg = browser.new_page()
        pg.route("https://cm.test/**", lambda route: route.fulfill(
            content_type="text/html",
            body=pages[2 if "site=2" in route.request.url else 1],
        ))
        yield pg
        browser.close()


def test_list_expansion_fills_rows_and_waits_for_user(page):
    a, a_foil, d = pc("A", 111, qty=2, cond="MT"), pc("A foil", 111, foil=True, lang="German"), pc("D", 444, price="0.02")
    missing = pc("Missing", 999)
    listed, prompts = [], []

    def confirm(summary):
        prompts.append(summary)
        if len(prompts) == 1:  # premier passage page 1 : on vérifie ce qui a été rempli
            assert page.input_value('select[name="idLanguage[0]"]') == "2"
            assert page.input_value('select[name="idCondition[0]"]') == "1"
            assert page.input_value('input[name="amount[0]"]') == "2"
            assert page.input_value('input[name="price[0]"]') == "1.50"
            assert not page.is_checked('input[name="isFoil[0]"]')
            assert page.input_value('input[name="amount[1]"]') == "0"  # ligne non concernée
        if len(prompts) == 2:  # deuxième variante de la même carte, même page rechargée
            assert page.is_checked('input[name="isFoil[0]"]')
            assert page.input_value('select[name="idLanguage[0]"]') == "3"
        return True

    not_done = list_expansion(
        page, 3660, [a, a_foil, d, missing], confirm=confirm, on_listed=listed.extend,
        wait_login=lambda: pytest.fail("pas de connexion attendue"), base_url="https://cm.test/B",
        slow=False, log=lambda s: None,
    )
    assert len(prompts) == 3
    assert [p.card.name for p in listed] == ["A", "A foil", "D"]
    assert [p.card.name for p in not_done] == ["Missing"]


def test_refused_batch_is_not_recorded(page):
    listed = []
    not_done = list_expansion(
        page, 3660, [pc("A", 111)], confirm=lambda s: False, on_listed=listed.extend,
        wait_login=lambda: None, base_url="https://cm.test/B", slow=False, log=lambda s: None,
    )
    assert listed == [] and [p.card.name for p in not_done] == ["A"]
