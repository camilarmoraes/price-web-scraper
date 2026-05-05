"""Testes unitários do parser de preço brasileiro."""

import pytest

from price_crawler.parsers import parse_price_br


class TestParsePriceBr:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("R$ 1.234,56", 1234.56),
            ("R$ 29,90", 29.9),
            ("R$ 7.299,00", 7299.0),
            ("R$ 100,00", 100.0),
            ("R$ 12.345,67", 12345.67),
            ("De: R$ 999,99 por: R$ 749,90", 999.99),  # primeiro match
            ("Apenas R$ 49,90 hoje", 49.9),
        ],
    )
    def test_parses_valid_prices(self, text: str, expected: float) -> None:
        assert parse_price_br(text) == expected

    @pytest.mark.parametrize("text", ["", "sem preço", "1234,56", "USD 100", None])
    def test_returns_none_for_invalid(self, text) -> None:
        assert parse_price_br(text) is None
