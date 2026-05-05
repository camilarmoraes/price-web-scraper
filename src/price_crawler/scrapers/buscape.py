"""Scraper do Buscapé (buscape.com.br).

Fluxo em dois passos:
  1. Página de busca  → lista de produtos com URLs de produto no Buscapé
  2. Página de produto → ofertas por loja com link de redirect para a loja real
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from price_crawler.browser import fetch_html
from price_crawler.parsers import parse_price_br

logger = logging.getLogger(__name__)


class BuscapeScraper:
    """Extrai preços e links de lojas no Buscapé."""

    name = "buscape"
    SEARCH_URL = "https://www.buscape.com.br/search?q={query}"
    BASE_URL = "https://www.buscape.com.br"

    def search(self, product_name: str, max_results: int = 5) -> list[dict]:
        url = self.SEARCH_URL.format(query=quote_plus(product_name))
        logger.info("[Buscapé] Buscando: %s", url)

        html = fetch_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        return self.parse_search_results(soup, max_results)

    def get_store_offers(self, product_page_url: str, max_offers: int = 5) -> list[dict]:
        logger.info("[Buscapé] Extraindo ofertas de: %s", product_page_url)
        html = fetch_html(product_page_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        return self.parse_offer_list(soup, product_page_url, max_offers)

    def parse_search_results(self, soup: BeautifulSoup, max_results: int) -> list[dict]:
        cards = (
            soup.select("[class*='ProductCard']")
            or soup.select("[data-testid='product-card']")
            or soup.select("li[class*='product']")
            or soup.select("[class*='SearchResult']")
        )
        if not cards:
            logger.warning("[Buscapé] Nenhum card encontrado no HTML de busca")
            return []

        results: list[dict] = []
        for card in cards[: max_results * 3]:
            parsed = self._parse_search_card(card)
            if parsed:
                results.append(parsed)
            if len(results) >= max_results:
                break
        return results

    def parse_offer_list(
        self, soup: BeautifulSoup, product_page_url: str, max_offers: int
    ) -> list[dict]:
        title_el = soup.select_one("h1")
        product_title = title_el.get_text(strip=True) if title_el else "Produto"

        offers_container = (
            soup.select("[class*='OfferList'] [class*='OfferCard']")
            or soup.select("[class*='offer-list'] [class*='offer']")
            or soup.select("[class*='StoreList'] li")
            or soup.select("[data-testid='offer-card']")
            or soup.select("[class*='Offer']")
        )
        if not offers_container:
            logger.warning("[Buscapé] Nenhuma oferta encontrada em %s", product_page_url)
            return []

        results: list[dict] = []
        for offer in offers_container[: max_offers * 2]:
            parsed = self._parse_offer_card(offer, product_title)
            if parsed:
                results.append(parsed)
            if len(results) >= max_offers:
                break
        return results

    def _parse_search_card(self, card) -> dict | None:
        title_el = (
            card.select_one("[class*='ProductCard__Name']")
            or card.select_one("[class*='Title']")
            or card.select_one("h2")
            or card.select_one("h3")
        )
        title = title_el.get_text(strip=True) if title_el else None

        price_el = card.select_one("[class*='Price']") or card.select_one("[class*='price']")
        price = parse_price_br(price_el.get_text(strip=True) if price_el else "")

        link_el = card.select_one("a[href]")
        href = link_el["href"] if link_el else None
        if href and not href.startswith("http"):
            href = self.BASE_URL + href

        if not title or not href:
            return None
        return {"title": title, "store": "Buscapé", "url": href, "price": price}

    def _parse_offer_card(self, offer, product_title: str) -> dict | None:
        store_el = (
            offer.select_one("[class*='StoreName']")
            or offer.select_one("[class*='store-name']")
            or offer.select_one("[class*='merchant']")
            or offer.select_one("img[alt]")  # logo da loja com alt=nome
        )
        store_name = (
            (store_el.get("alt") or store_el.get_text(strip=True)) if store_el else "Loja"
        )

        price_el = offer.select_one("[class*='Price']") or offer.select_one("[class*='price']")
        price = parse_price_br(price_el.get_text(strip=True) if price_el else "")

        # Buscapé usa links de tracking que redirecionam para a loja real
        buy_link = (
            offer.select_one("a[href*='/click/']")
            or offer.select_one("a[href*='tracker']")
            or offer.select_one("a[class*='Buy']")
            or offer.select_one("a[class*='buy']")
            or offer.select_one("a[class*='Comprar']")
            or offer.select_one("a[href]")
        )
        href = buy_link["href"] if buy_link else None
        if href and not href.startswith("http"):
            href = self.BASE_URL + href

        if price is None or not href:
            return None
        return {"title": product_title, "store": store_name, "url": href, "price": price}
