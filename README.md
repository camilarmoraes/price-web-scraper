# 💸 price-crawler

> Web scraper que consolida ofertas dos comparadores brasileiros **Zoom** e **Buscapé** numa base histórica local, com bypass de detecção anti-bot e dashboard interativo em Streamlit.

<!-- Substitua por um GIF do dashboard funcionando: docs/images/dashboard.gif -->
![dashboard](docs/images/dashboard.png)

---

## O problema

Comparadores brasileiros não expõem API pública, os preços oscilam constantemente e cada site usa um conjunto de seletores CSS diferente — que muda quando o time de frontend faz deploy. Quem quer:

- Comparar ofertas de várias lojas para um produto específico,
- Acompanhar a evolução do preço ao longo do tempo,
- Ou simplesmente extrair o link real da loja (sem o redirect de tracking),

precisa fazer scraping resiliente, com renderização de JavaScript e bypass de detecção anti-bot.

## A solução

Pipeline completo em Python:

1. **Busca** o produto no Zoom (com Buscapé como fallback);
2. Para cada candidato, abre a página de produto e **extrai ofertas por loja**;
3. **Segue o redirect** de tracking via Playwright headless até a URL real do e-commerce;
4. **Persiste** no SQLite local com timestamp — formando uma série histórica de preços;
5. Dashboard Streamlit consulta a base e plota a **evolução de preços** por loja.

## Stack

| Camada           | Tecnologia                                        |
|------------------|---------------------------------------------------|
| Scraping         | Playwright (Chromium headless) + BeautifulSoup    |
| Configuração     | pydantic-settings + python-dotenv                 |
| Persistência     | SQLite (stdlib `sqlite3`)                         |
| UI               | Streamlit + pandas                                |
| Testes           | pytest com fixtures HTML offline                  |
| Empacotamento    | [uv](https://docs.astral.sh/uv/) + hatchling      |

## Como rodar

Pré-requisito: Python 3.11+ e [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone <repo>
cd crawler-buscador-preco

uv sync                              # cria o venv e instala as deps a partir do uv.lock
uv run playwright install chromium   # baixa o browser usado pelo Playwright

uv run streamlit run app/streamlit_app.py
```

Configurações via `.env` (copie de `.env.example`):

```bash
HEADLESS=true
WAIT_MS=3000
TIMEOUT_MS=30000
DB_PATH=./price_results.db
RESOLVE_STORE_URL=true
MAX_RESULTS_PER_ITEM=5
```

## Uso programático

```python
from price_crawler import PriceSearchService

service = PriceSearchService()
results = service.search_one("iphone 15 128gb")

for r in results:
    print(f"{r.store:20} R$ {r.price:>8.2f}  {r.url}")
```

## Decisões técnicas

**Por que Playwright e não `requests`?**
Tanto o Zoom quanto o Buscapé renderizam os cards de produto via JavaScript. Um GET cru retorna HTML quase vazio. Playwright também permite injetar scripts de stealth (`navigator.webdriver = undefined`, `chrome.runtime`, etc.) para reduzir bloqueios.

**Por que seletores em cascata com `[class*=...]` e `data-testid`?**
Os comparadores usam **CSS Modules**: `OfferCard__container_a3f7b` muda a cada deploy. Em vez de fixar a classe inteira, o scraper combina:
- `data-testid="..."` (o mais estável, usado pelo time de QA do site);
- `[class*='OfferCard']` (substring match, sobrevive a hashes);
- Fallbacks em ordem de probabilidade.

Isso reduz drasticamente a manutenção quando o layout muda.

**Por que `follow_redirect`?**
O link "Comprar" no Buscapé/Zoom é `/click/abc123` — um redirect com tracking de afiliado. Para guardar o link **real** do e-commerce na base, abrimos a URL com Playwright e esperamos `location.hostname` sair do domínio do comparador.

**Por que SQLite?**
Zero-setup (qualquer recrutador clona e roda), mas estruturado o suficiente para manter histórico temporal. O schema indexa `(product_query, queried_at)` para a consulta principal do dashboard. Se o projeto crescer, a substituição por Postgres é trivial — `SQLiteRepository` está atrás de uma interface implícita usada pelo `PriceSearchService`.

## Arquitetura

Veja [`docs/architecture.md`](docs/architecture.md) para o diagrama detalhado.

```
┌─────────────────┐
│ Streamlit UI    │── busca produto ──▶ PriceSearchService
└─────────────────┘                            │
                                               ▼
                              ┌──────────────────────────────┐
                              │  ZoomScraper / BuscapeScraper│  (fallback em cadeia)
                              └────────────┬─────────────────┘
                                           │ HTML
                              ┌────────────▼─────────────────┐
                              │ Playwright (headless+stealth)│
                              └────────────┬─────────────────┘
                                           │ ofertas + redirect
                              ┌────────────▼─────────────────┐
                              │  SQLiteRepository            │ ── price_results.db
                              └──────────────────────────────┘
```

## Testes

Os testes rodam **offline**: HTMLs salvos em `tests/fixtures/` reproduzem a estrutura crítica das páginas. Sem rede, sem Playwright nos testes — determinísticos e rápidos.

```bash
uv run pytest -v
```

```
26 passed in 0.54s
```

## Estrutura

```
src/price_crawler/
├── browser.py        # Playwright wrappers (fetch + follow_redirect)
├── parsers.py        # parse_price_br
├── models.py         # Offer, PriceResult
├── service.py        # PriceSearchService — orquestrador
├── scrapers/
│   ├── base.py       # Protocol Scraper
│   ├── zoom.py
│   └── buscape.py
└── storage/
    ├── sqlite_repo.py
    └── exporters.py  # to_csv, to_json
app/streamlit_app.py
tests/                # pytest + fixtures HTML
legacy/               # versão monolítica original (referência)
```

## Próximos passos

- Adicionar mais comparadores (Mercado Livre, Kabum) — basta implementar o `Scraper` Protocol.
- Agendamento via cron / GitHub Actions para gerar série temporal real.
- Alertas (Telegram/email) quando o preço cai abaixo de um limite.
- Dockerfile com Playwright + Chromium pré-instalados.
