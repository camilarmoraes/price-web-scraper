"""Price crawler — scraper de ofertas dos comparadores brasileiros Zoom e Buscapé."""

from price_crawler.models import Offer, PriceResult
from price_crawler.service import PriceSearchService

__all__ = ["Offer", "PriceResult", "PriceSearchService"]
__version__ = "0.1.0"
