"""Repositório SQLite — auto-cria schema na primeira execução."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path

from price_crawler.models import PriceResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    queried_at    TEXT    NOT NULL,
    product_query TEXT    NOT NULL,
    product_title TEXT    NOT NULL,
    store         TEXT    NOT NULL,
    price         REAL    NOT NULL,
    url           TEXT    NOT NULL,
    source        TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_price_results_query
    ON price_results(product_query, queried_at);
"""


class SQLiteRepository:
    """Persistência local em SQLite. Pensado para histórico temporal de preços."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def insert_many(self, results: Iterable[PriceResult]) -> int:
        rows = [
            (
                r.queried_at.isoformat(timespec="seconds"),
                r.product_query,
                r.product_title,
                r.store,
                r.price,
                r.url,
                r.source,
            )
            for r in results
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO price_results "
                "(queried_at, product_query, product_title, store, price, url, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def query_history(self, product_query: str) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT queried_at, product_title, store, price, url, source "
                "FROM price_results WHERE product_query = ? ORDER BY queried_at",
                (product_query,),
            )
            return [dict(row) for row in cur.fetchall()]

    def latest_per_store(self, product_query: str) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT store, price, url, source, MAX(queried_at) AS queried_at
                FROM price_results
                WHERE product_query = ?
                GROUP BY store
                ORDER BY price ASC
                """,
                (product_query,),
            )
            return [dict(row) for row in cur.fetchall()]

    def list_queries(self) -> list[str]:
        """Lista distinct product_query, mais recente primeiro."""
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT product_query, MAX(queried_at) AS last "
                "FROM price_results GROUP BY product_query ORDER BY last DESC"
            )
            return [row["product_query"] for row in cur.fetchall()]
