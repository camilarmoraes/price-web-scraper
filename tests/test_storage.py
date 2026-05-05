"""Testes de SQLiteRepository e exporters — usam tmp_path do pytest."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from price_crawler.models import PriceResult
from price_crawler.storage import SQLiteRepository, to_csv, to_json


def _result(query: str, store: str, price: float, when: datetime) -> PriceResult:
    return PriceResult(
        product_query=query,
        product_title=f"{query} (modelo X)",
        store=store,
        price=price,
        url=f"https://{store.lower()}.com/p/{query.replace(' ', '-')}",
        source="zoom",
        queried_at=when,
    )


class TestSQLiteRepository:
    def test_insert_e_history(self, tmp_path: Path) -> None:
        repo = SQLiteRepository(tmp_path / "test.db")
        now = datetime(2026, 5, 5, 12, 0, 0)

        repo.insert_many(
            [
                _result("iphone 15", "Magalu", 7299.00, now),
                _result("iphone 15", "Amazon", 7349.00, now + timedelta(days=1)),
                _result("iphone 15", "Magalu", 6999.00, now + timedelta(days=7)),
            ]
        )

        history = repo.query_history("iphone 15")
        assert len(history) == 3
        # Ordenado por queried_at ASC
        assert history[0]["price"] == 7299.00
        assert history[-1]["price"] == 6999.00

    def test_latest_per_store(self, tmp_path: Path) -> None:
        repo = SQLiteRepository(tmp_path / "test.db")
        now = datetime(2026, 5, 5, 12, 0, 0)

        repo.insert_many(
            [
                _result("notebook", "Kabum", 4500.00, now),
                _result("notebook", "Kabum", 4299.00, now + timedelta(days=2)),
                _result("notebook", "Magalu", 4399.00, now + timedelta(days=2)),
            ]
        )

        latest = repo.latest_per_store("notebook")
        assert len(latest) == 2
        # ordem por preço ASC
        assert latest[0]["store"] == "Kabum"
        assert latest[0]["price"] == 4299.00

    def test_list_queries(self, tmp_path: Path) -> None:
        repo = SQLiteRepository(tmp_path / "test.db")
        now = datetime(2026, 5, 5, 12, 0, 0)
        repo.insert_many([_result("a", "L1", 10.0, now), _result("b", "L2", 20.0, now)])
        assert set(repo.list_queries()) == {"a", "b"}

    def test_schema_persistente(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        repo1 = SQLiteRepository(db)
        repo1.insert_many([_result("teste", "L", 1.0, datetime(2026, 5, 5))])

        # Reabrir não recria nem apaga dados
        repo2 = SQLiteRepository(db)
        assert len(repo2.query_history("teste")) == 1


class TestExporters:
    def test_to_csv_inclui_header_e_linhas(self, tmp_path: Path) -> None:
        results = [
            _result("iphone", "Magalu", 7299.00, datetime(2026, 5, 5, 12, 0, 0)),
            _result("iphone", "Amazon", 7349.00, datetime(2026, 5, 5, 12, 0, 0)),
        ]
        path = to_csv(results, tmp_path / "out.csv")
        content = path.read_text(encoding="utf-8")

        assert "queried_at,product_query" in content
        assert "Magalu" in content
        assert "7299.0" in content

    def test_to_json_serializa_datetime(self, tmp_path: Path) -> None:
        results = [_result("iphone", "Magalu", 7299.00, datetime(2026, 5, 5, 12, 0, 0))]
        path = to_json(results, tmp_path / "out.json")
        data = json.loads(path.read_text(encoding="utf-8"))

        assert len(data) == 1
        assert data[0]["queried_at"] == "2026-05-05T12:00:00"
        assert data[0]["price"] == 7299.00
