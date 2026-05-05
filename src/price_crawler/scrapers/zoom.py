"""Scraper do Zoom.com.br."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from price_crawler.browser import fetch_html
from price_crawler.parsers import parse_price_br

logger = logging.getLogger(__name__)


class ZoomScraper:
    """Extrai preços e links de lojas no Zoom.com.br."""

    name = "zoom"
    SEARCH_URL = "https://www.zoom.com.br/search?q={query}"
    BASE_URL = "https://www.zoom.com.br"

    def search(self, product_name: str, max_results: int = 5) -> list[dict]:
        url = self.SEARCH_URL.format(query=quote_plus(product_name))
        logger.info("[Zoom] Buscando: %s", url)

        html = fetch_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        return self.parse_search_results(soup, max_results)

    def get_store_offers(self, product_page_url: str, max_offers: int = 5) -> list[dict]:
        logger.info("[Zoom] Extraindo ofertas de: %s", product_page_url)
        html = fetch_html(product_page_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        return self.parse_offer_list(soup, product_page_url, max_offers)

    def parse_search_results(self, soup: BeautifulSoup, max_results: int) -> list[dict]:
        # data-testid é estável mesmo quando os nomes das classes CSS mudam (CSS Modules)
        cards = soup.select("article[data-testid='product-card']")
        if not cards:
            logger.warning("[Zoom] Nenhum card encontrado no HTML")
            return []

        results: list[dict] = []
        for card in cards[: max_results * 3]:
            parsed = self._parse_card(card)
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
            or soup.select("[data-testid='offer-card']")
            or soup.select("[class*='Offer']")
            or soup.select("[class*='StoreList'] li")
        )
        if not offers_container:
            logger.warning("[Zoom] Nenhuma oferta encontrada em %s", product_page_url)
            return []

        results: list[dict] = []
        for offer in offers_container[: max_offers * 2]:
            parsed = self._parse_offer_card(offer, product_title)
            if parsed:
                results.append(parsed)
            if len(results) >= max_offers:
                break
        return results

    def _parse_card(self, card) -> dict | None:
        title_el = card.select_one("[data-testid='product-card::name']")
        title = title_el.get_text(strip=True) if title_el else None

        price_el = card.select_one("[data-testid='product-card::price'] strong") or card.select_one(
            "[data-testid='product-card::price']"
        )
        price = parse_price_br(price_el.get_text(strip=True) if price_el else "")

        store_el = card.select_one("[aria-label='Menor preço'] span")
        store_name = store_el.get_text(strip=True) if store_el else "Zoom"

        link_el = card.select_one("a[data-testid='product-card::card']")
        href = link_el["href"] if link_el else None
        if href and not href.startswith("http"):
            href = self.BASE_URL + href

        if not title or price is None or not href:
            return None
        return {"title": title, "store": store_name, "url": href, "price": price}

    def _parse_offer_card(self, offer, product_title: str) -> dict | None:
        store_el = (
            offer.select_one("[class*='StoreName']")
            or offer.select_one("[class*='store-name']")
            or offer.select_one("[class*='merchant']")
            or offer.select_one("img[alt]")
        )
        store_name = (
            (store_el.get("alt") or store_el.get_text(strip=True)) if store_el else "Loja"
        )

        price_el = offer.select_one("[class*='Price']") or offer.select_one("[class*='price']")
        price = parse_price_br(price_el.get_text(strip=True) if price_el else "")

        buy_link = (
            offer.select_one("a[href*='/click/']")
            or offer.select_one("a[href*='tracker']")
            or offer.select_one("a[class*='Buy']")
            or offer.select_one("a[class*='buy']")
            or offer.select_one("a[href]")
        )
        href = buy_link["href"] if buy_link else None
        if href and not href.startswith("http"):
            href = self.BASE_URL + href

        if price is None or not href:
            return None
        return {"title": product_title, "store": store_name, "url": href, "price": price}
