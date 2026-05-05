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

    def test_descarta_cards_patrocinados_com_lead(self) -> None:
        # Cards patrocinados linkam direto pra /lead?oid=... (redirect afiliado);
        # não são páginas de detalhe, então não dá pra extrair ofertas deles.
        html = """
        <article data-testid='product-card'>
          <a data-testid='product-card::card'
             href='https://www.zoom.com.br/lead?oid=123&vtex=true'></a>
          <span data-testid='product-card::name'>Patrocinado</span>
          <span data-testid='product-card::price'><strong>R$ 1.999,00</strong></span>
        </article>
        <article data-testid='product-card'>
          <a data-testid='product-card::card' href='/geladeira/foo?_lc=88'></a>
          <span data-testid='product-card::name'>Geladeira Foo</span>
          <span data-testid='product-card::price'><strong>R$ 2.999,00</strong></span>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        results = ZoomScraper().parse_search_results(soup, max_results=5)
        assert len(results) == 1
        assert "/lead?" not in results[0]["url"]
        assert results[0]["title"] == "Geladeira Foo"


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
