"""Orquestra a busca: scrapers em cascata → resolve redirects → persiste."""

from __future__ import annotations

import logging

from price_crawler.browser import follow_redirect
from price_crawler.config import settings
from price_crawler.models import PriceResult
from price_crawler.scrapers import BuscapeScraper, Scraper, ZoomScraper
from price_crawler.storage.sqlite_repo import SQLiteRepository

logger = logging.getLogger(__name__)


class PriceSearchService:
    """Busca um produto nos comparadores e persiste as ofertas resolvidas."""

    def __init__(
        self,
        repository: SQLiteRepository | None = None,
        scrapers: list[Scraper] | None = None,
        max_results_per_item: int | None = None,
        resolve_store_url: bool | None = None,
    ) -> None:
        self.repository = repository or SQLiteRepository(settings.db_path)
        self.scrapers: list[Scraper] = scrapers or [ZoomScraper(), BuscapeScraper()]
        self.max_results_per_item = max_results_per_item or settings.max_results_per_item
        self.resolve_store_url = (
            resolve_store_url if resolve_store_url is not None else settings.resolve_store_url
        )
        self._scraper_by_name = {s.name: s for s in self.scrapers}

    def search_one(self, product_name: str, persist: bool = True) -> list[PriceResult]:
        """Busca um produto, resolve ofertas, persiste e retorna os PriceResults."""
        logger.info("Buscando: %r", product_name)

        candidates = self._search_all(product_name)
        if not candidates:
            logger.warning("Nenhum resultado encontrado para %r", product_name)
            return []

        offers = self._resolve_offers(candidates)
        results = [
            PriceResult(
                product_query=product_name,
                product_title=o["title"],
                store=o["store"],
                price=float(o["price"]),
                url=o["url"],
                source=o["source"],
            )
            for o in offers
        ]

        if persist and results:
            inserted = self.repository.insert_many(results)
            logger.info("%d resultados persistidos.", inserted)

        return results

    def _search_all(self, product_name: str) -> list[dict]:
        """Tenta cada scraper em ordem; retorna assim que um deles produz resultados."""
        for scraper in self.scrapers:
            results = scraper.search(product_name, max_results=self.max_results_per_item)
            if results:
                for r in results:
                    r["source"] = scraper.name
                logger.info("[%s] %d resultados", scraper.name, len(results))
                return results
            logger.info("[%s] sem resultados — tentando próximo scraper", scraper.name)
        return []

    def _resolve_offers(self, candidates: list[dict]) -> list[dict]:
        """Para cada candidato, abre a página de produto e expande em ofertas por loja.

        Quando `resolve_store_url=True`, segue o redirect de tracking até a URL real
        da loja (mais lento, mas o link fica direto para o e-commerce).
        """
        if not self.resolve_store_url:
            return candidates

        resolved: list[dict] = []
        seen_urls: set[str] = set()

        for c in candidates:
            scraper = self._scraper_by_name.get(c.get("source", ""))
            if scraper is None:
                continue

            offers = scraper.get_store_offers(c["url"], max_offers=2)
            for offer in offers:
                url = offer.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                offer["source"] = c["source"]
                offer["url"] = follow_redirect(url)
                resolved.append(offer)
                logger.info("Link final: %s", offer["url"])

        return resolved
