"""Testa os parsers do BuscapeScraper offline com HTMLs em `tests/fixtures/`."""

from bs4 import BeautifulSoup

from price_crawler.scrapers.buscape import BuscapeScraper


class TestBuscapeSearch:
    def test_extrai_cards_de_busca(self, buscape_search_html: str) -> None:
        soup = BeautifulSoup(buscape_search_html, "html.parser")
        results = BuscapeScraper().parse_search_results(soup, max_results=5)

        assert len(results) == 3
        for r in results:
            assert r["title"]
            assert r["url"].startswith("https://www.buscape.com.br/")
            assert r["price"] > 0


    def test_descarta_cards_patrocinados_com_lead(self) -> None:
        # Cards patrocinados linkam direto pra /lead?oid=... (redirect afiliado);
        # não são páginas de detalhe, então não dá pra extrair ofertas deles.
        html = """
        <div class='ProductCard'>
          <a href='https://www.buscape.com.br/lead?oid=123&vtex=true'>
            <h2 class='Title'>Patrocinado: Geladeira Foo</h2>
          </a>
          <span class='Price'>R$ 1.999,00</span>
        </div>
        <div class='ProductCard'>
          <a href='/geladeira/foo?_lc=88'>
            <h2 class='Title'>Geladeira Bar</h2>
          </a>
          <span class='Price'>R$ 2.999,00</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        results = BuscapeScraper().parse_search_results(soup, max_results=5)
        assert len(results) == 1
        assert "/lead?" not in results[0]["url"]
        assert results[0]["title"] == "Geladeira Bar"


class TestBuscapeOfferList:
    def test_extrai_ofertas_com_seletores_diversos(self, buscape_product_html: str) -> None:
        soup = BeautifulSoup(buscape_product_html, "html.parser")
        offers = BuscapeScraper().parse_offer_list(
            soup, "https://www.buscape.com.br/p", max_offers=5
        )

        assert len(offers) == 3

        # Cada oferta usa um caminho diferente para identificar a loja
        # (StoreName, img[alt], merchant-name)
        stores = {o["store"] for o in offers}
        assert "Magalu" in stores
        assert "Americanas" in stores  # via img[alt]
        assert "Submarino" in stores  # via merchant-name

        for o in offers:
            assert o["price"] > 0
            assert o["url"].startswith("https://www.buscape.com.br/click/")
            assert o["title"] == 'Smart TV LG 50" 4K UHD'

    def test_html_sem_ofertas_retorna_vazio(self) -> None:
        soup = BeautifulSoup("<html><body><h1>Produto</h1></body></html>", "html.parser")
        offers = BuscapeScraper().parse_offer_list(
            soup, "https://www.buscape.com.br/p", max_offers=5
        )
        assert offers == []
