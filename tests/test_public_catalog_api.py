from types import SimpleNamespace

from api.production import public_catalog_api
from api.production.public_catalog_api import router as public_catalog_router


def test_public_catalog_routes_are_defined():
    paths = {route.path for route in public_catalog_router.routes}
    assert "/api/public/catalog/products" in paths
    assert "/api/public/catalog/products/{sku}" in paths


def test_public_catalog_module_is_read_only():
    source = open("api/production/public_catalog_api.py", encoding="utf-8").read()
    assert "INSERT INTO" not in source
    assert "UPDATE " not in source
    assert "DELETE FROM" not in source


def test_public_catalog_router_is_registered_in_production_app():
    source = open("api/production/main.py", encoding="utf-8").read()
    assert "app.include_router(public_catalog_router)" in source


def test_public_catalog_does_not_expose_retail_or_trade_prices():
    source = open("api/production/public_catalog_api.py", encoding="utf-8").read()
    assert "retail_price" not in source
    assert "distribution_price" not in source
    assert "wholesale_price" not in source


class _FakeCursor:
    def __init__(self):
        self.description = []
        self._rows = []
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        self.queries.append(query)
        if "FROM eyt_product_master" in query:
            projection = query.split("FROM eyt_product_master", 1)[0].split("SELECT", 1)[1]
            names = [part.strip().split(".")[-1] for part in projection.replace("\\n", " ").split(",")]
            self.description = [SimpleNamespace(name=name) for name in names]
            row = {name: (1 if name == "id" else "test") for name in names}
            self._rows = [tuple(row[name] for name in names)]
        else:
            self.description = [SimpleNamespace(name="make")]
            self._rows = []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _FakeConnection:
    def __init__(self):
        self.cursor_instance = _FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_instance


def test_public_catalog_responses_never_include_prices(monkeypatch):
    connection = _FakeConnection()
    monkeypatch.setattr(public_catalog_api, "_connect", lambda: connection)

    listing = public_catalog_api.list_public_products()
    detail = public_catalog_api.get_public_product("TEST-SKU")

    forbidden = {"retail_price", "distribution_price", "wholesale_price"}
    assert listing["items"]
    assert forbidden.isdisjoint(listing["items"][0])
    assert forbidden.isdisjoint(detail)
    # Arbitrary JSON attributes are not a safe public contract: they may later
    # contain internal prices, costs, supplier notes, or other private metadata.
    assert "attributes" not in listing["items"][0]
    assert "attributes" not in detail
    product_queries = [
        query for query in connection.cursor_instance.queries
        if "FROM eyt_product_master" in query
    ]
    assert len(product_queries) == 2
    assert all(not (forbidden & set(query.split())) for query in product_queries)
