"""Estruturas de dados trocadas entre scrapers, service e storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Offer:
    """Oferta bruta extraída de uma página de produto do comparador."""

    title: str
    store: str
    url: str
    price: float
    source: str  # "zoom" | "buscape"


@dataclass
class PriceResult:
    """Resultado consolidado e persistível, com timestamp de captura."""

    product_query: str
    product_title: str
    store: str
    price: float
    url: str
    source: str
    queried_at: datetime = field(default_factory=datetime.utcnow)
