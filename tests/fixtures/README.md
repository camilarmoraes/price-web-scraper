# Fixtures HTML

Estes arquivos são HTML reduzidos que reproduzem a estrutura crítica das páginas do Zoom e Buscapé — apenas os seletores que os scrapers usam.

Para capturar HTMLs **reais** do site (mais robusto, porém pode quebrar quando o layout muda):

```python
from price_crawler.browser import fetch_html
from pathlib import Path

html = fetch_html("https://www.zoom.com.br/search?q=iphone+15")
Path("tests/fixtures/zoom_search.html").write_text(html, encoding="utf-8")
```
