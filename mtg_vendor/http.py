"""Accès HTTP minimal (bibliothèque standard uniquement)."""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

USER_AGENT = "mtg-vendor/0.1"


def get_json(url: str, timeout: float = 60) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def post_json(url: str, payload: Any, timeout: float = 60) -> Any:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def polite_pause(seconds: float = 0.1) -> None:
    """Scryfall demande 50 à 100 ms entre deux requêtes."""
    time.sleep(seconds)
