"""Helpers de parsing puros — testáveis offline, sem dependência de browser."""

from __future__ import annotations

import re

_PRICE_BR_RE = re.compile(r"R\$\s*([\d.]+,\d{2})")


def parse_price_br(text: str) -> float | None:
    """Converte preço em formato brasileiro para float.

    Exemplos: 'R$ 1.234,56' → 1234.56 | 'R$ 29,90' → 29.9
    """
    match = _PRICE_BR_RE.search(text or "")
    if not match:
        return None
    return float(match.group(1).replace(".", "").replace(",", "."))
