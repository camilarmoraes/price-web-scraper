"""Camada de browser via Playwright. Encapsula fetch e follow-redirect."""

from __future__ import annotations

import contextlib
import logging

from playwright.sync_api import sync_playwright

from price_crawler.config import settings

logger = logging.getLogger(__name__)

_USER_AGENT_CHROME_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_USER_AGENT_CHROME_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_STEALTH_INIT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt'] });
    window.chrome = { runtime: {} };
"""

_COMPARATOR_DOMAINS = ("zoom.com.br", "buscape.com.br")


def fetch_html(url: str, wait_ms: int | None = None, timeout_ms: int | None = None) -> str | None:
    """Renderiza a página com Playwright e retorna o HTML (None em falha)."""
    wait_ms = wait_ms if wait_ms is not None else settings.wait_ms
    timeout_ms = timeout_ms if timeout_ms is not None else settings.timeout_ms

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=settings.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent=_USER_AGENT_CHROME_WIN,
                viewport={"width": 1366, "height": 768},
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
            )
            context.add_init_script(_STEALTH_INIT_SCRIPT)
            page = context.new_page()
            # "domcontentloaded" evita timeout em SPAs que mantêm conexões abertas
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)
            html = page.content()
            browser.close()
            return html
    except Exception as exc:
        logger.warning("Falha ao capturar HTML (%s): %s", url, exc)
        return None


def follow_redirect(url: str, timeout_ms: int | None = None) -> str:
    """Segue redirecionamentos JS dos comparadores e retorna a URL final da loja."""
    timeout_ms = timeout_ms if timeout_ms is not None else settings.timeout_ms

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            page = browser.new_page(user_agent=_USER_AGENT_CHROME_MAC)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # networkidle pode demorar; se estourar timeout, segue mesmo assim
            with contextlib.suppress(Exception):
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            # espera o redirect sair do domínio do comparador
            with contextlib.suppress(Exception):
                page.wait_for_function(
                    "() => "
                    + " && ".join(
                        f"!location.hostname.includes('{d}')" for d in _COMPARATOR_DOMAINS
                    ),
                    timeout=timeout_ms,
                )
            final_url = page.url
            browser.close()
            return final_url
    except Exception as exc:
        logger.warning("follow_redirect falhou (%s): %s", url, exc)
        return url
