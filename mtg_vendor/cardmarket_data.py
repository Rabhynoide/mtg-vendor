"""Fichiers publics de Cardmarket : catalogue des cartes et guide des prix (mis à jour chaque jour)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

from . import cache, http

PRICE_GUIDE_URL = "https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_1.json"
PRODUCTS_URL = "https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_1.json"


@dataclass(frozen=True)
class Product:
    id_product: int
    name: str
    id_expansion: int


@dataclass(frozen=True)
class Prices:
    avg30: Decimal | None
    avg30_foil: Decimal | None
    trend: Decimal | None
    trend_foil: Decimal | None


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


class CardmarketCatalog:
    def __init__(self, products: dict[int, Product], prices: dict[int, Prices]):
        self.products = products
        self.prices = prices

    @classmethod
    def from_json(cls, products_json: dict, prices_json: dict) -> "CardmarketCatalog":
        products = {
            p["idProduct"]: Product(p["idProduct"], p["name"], p["idExpansion"])
            for p in products_json["products"]
        }
        prices = {
            g["idProduct"]: Prices(
                avg30=_dec(g.get("avg30")),
                avg30_foil=_dec(g.get("avg30-foil")),
                trend=_dec(g.get("trend")),
                trend_foil=_dec(g.get("trend-foil")),
            )
            for g in prices_json["priceGuides"]
        }
        return cls(products, prices)

    @classmethod
    def load(cls, get_json: Callable[[str], Any] | None = None, max_age_hours: float = 20) -> "CardmarketCatalog":
        get_json = get_json or http.get_json
        products_json = cache.cached_json("cm_products.json", max_age_hours, lambda: get_json(PRODUCTS_URL))
        prices_json = cache.cached_json("cm_price_guide.json", max_age_hours, lambda: get_json(PRICE_GUIDE_URL))
        return cls.from_json(products_json, prices_json)
