"""Export de PriceResult para CSV/JSON usando só stdlib."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from price_crawler.models import PriceResult

_COLUMNS = ["queried_at", "product_query", "product_title", "store", "price", "url", "source"]


def to_csv(results: Iterable[PriceResult], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        writer.writeheader()
        for r in results:
            row = asdict(r)
            row["queried_at"] = r.queried_at.isoformat(timespec="seconds")
            writer.writerow(row)
    return path


def to_json(results: Iterable[PriceResult], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for r in results:
        row = asdict(r)
        row["queried_at"] = r.queried_at.isoformat(timespec="seconds")
        payload.append(row)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
