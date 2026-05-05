"""Scrapers por comparador. Adicionar um novo: implementar Scraper e registrar no service."""

from price_crawler.scrapers.base import Scraper
from price_crawler.scrapers.buscape import BuscapeScraper
from price_crawler.scrapers.zoom import ZoomScraper

__all__ = ["BuscapeScraper", "Scraper", "ZoomScraper"]
