"""Fixtures compartilhadas — carregam os HTMLs salvos em `tests/fixtures/`."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def zoom_search_html() -> str:
    return _load("zoom_search.html")


@pytest.fixture
def zoom_product_html() -> str:
    return _load("zoom_product.html")


@pytest.fixture
def buscape_search_html() -> str:
    return _load("buscape_search.html")


@pytest.fixture
def buscape_product_html() -> str:
    return _load("buscape_product.html")
