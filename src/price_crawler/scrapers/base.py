"""Contrato comum aos scrapers (Zoom, Buscapé, futuros)."""

from __future__ import annotations

from typing import Protocol


class Scraper(Protocol):
    """Interface mínima que todo scraper de comparador deve satisfazer.

    O `name` identifica a fonte nos resultados ("zoom", "buscape", ...) e é
    usado pelo service para roteamento durante a resolução de redirects.
    """

    name: str

    def search(self, product_name: str, max_results: int = 5) -> list[dict]:
        """Lista produtos da página de busca: title, store, url, price."""

    def get_store_offers(self, product_page_url: str, max_offers: int = 5) -> list[dict]:
        """Extrai ofertas por loja na página de produto: title, store, url, price."""
