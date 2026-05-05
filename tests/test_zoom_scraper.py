"""Testa os parsers do ZoomScraper offline com HTMLs em `tests/fixtures/`."""

from bs4 import BeautifulSoup

from price_crawler.scrapers.zoom import ZoomScraper


class TestZoomSearch:
    def test_extrai_cards_de_busca(self, zoom_search_html: str) -> None:
        soup = BeautifulSoup(zoom_search_html, "html.parser")
        results = ZoomScraper().parse_search_results(soup, max_results=5)

        assert len(results) == 3
        for r in results:
            assert r["title"]
            assert r["price"] > 0
            assert r["url"].startswith("https://")
            assert r["store"]

    def test_resolve_links_relativos(self, zoom_search_html: str) -> None:
        soup = BeautifulSoup(zoom_search_html, "html.parser")
        results = ZoomScraper().parse_search_results(soup, max_results=5)

        for r in results:
            assert r["url"].startswith("https://www.zoom.com.br/")

    def test_respeita_max_results(self, zoom_search_html: str) -> None:
        soup = BeautifulSoup(zoom_search_html, "html.parser")
        results = ZoomScraper().parse_search_results(soup, max_results=2)
        assert len(results) == 2

    def test_html_vazio_retorna_lista_vazia(self) -> None:
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert ZoomScraper().parse_search_results(soup, max_results=5) == []


class TestZoomOfferList:
    def test_extrai_ofertas_por_loja(self, zoom_product_html: str) -> None:
        soup = BeautifulSoup(zoom_product_html, "html.parser")
        offers = ZoomScraper().parse_offer_list(soup, "https://www.zoom.com.br/x", max_offers=5)

        assert len(offers) == 3
        stores = {o["store"] for o in offers}
        assert {"Magazine Luiza", "Amazon", "Casas Bahia"} <= stores

        for o in offers:
            assert o["price"] > 0
            assert "/click/" in o["url"]
            assert o["title"] == "iPhone 15 Pro 128GB"
