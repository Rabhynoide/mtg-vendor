"""Petit cache de fichiers JSON sur disque."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable


def cache_dir() -> Path:
    base = os.environ.get("MTG_VENDOR_CACHE") or Path.home() / ".cache" / "mtg-vendor"
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def cached_json(name: str, max_age_hours: float, fetch: Callable[[], Any]) -> Any:
    """Renvoie le JSON en cache s'il a moins de max_age_hours, sinon le télécharge."""
    path = cache_dir() / name
    if path.exists() and time.time() - path.stat().st_mtime < max_age_hours * 3600:
        return json.loads(path.read_text(encoding="utf-8"))
    data = fetch()
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def load_json(name: str, default: Any) -> Any:
    path = cache_dir() / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(name: str, data: Any) -> None:
    (cache_dir() / name).write_text(json.dumps(data), encoding="utf-8")
