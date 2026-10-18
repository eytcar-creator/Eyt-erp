from types import SimpleNamespace

from api.production import vehicle_master_api


class _Cursor:
    def __init__(self):
        self.description = []
        self.rows = []
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        self.queries.append(query)
        if "SELECT id FROM vehicle_master" in query:
            self.description = [SimpleNamespace(name="id")]
            self.rows = [("vehicle-uuid",)]
            return
        self.description = [
            SimpleNamespace(name=name)
            for name in (
                "productId", "productCode", "sku", "nameFa", "nameEn",
                "productType", "unit", "barcode", "oemCode", "specification",
                "categoryCode", "categoryNameFa", "position", "side", "yearFrom", "yearTo",
            )
        ]
        self.rows = [(
            "product-uuid", "EYT-TEST", "TEST-SKU", "قطعه آزمایشی", "Test part",
            "PART", "عدد", "123", "OEM-1", "spec", "SUSP", "تعلیق",
            "FRONT", "LEFT", 2020, 2025,
        )]

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self):
        self.cur = _Cursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cur


def test_public_vehicle_fitment_does_not_select_or_return_base_price(monkeypatch):
    connection = _Connection()
    monkeypatch.setattr(vehicle_master_api, "_connect", lambda: connection)

    products = vehicle_master_api.catalog_vehicle_products("TEST-VEHICLE")

    assert products
    assert "salePrice" not in products[0]
    assert "sale_price" not in products[0]
    product_query = next(q for q in connection.cur.queries if "product_vehicle_compatibility" in q)
    assert "sale_price" not in product_query.lower()
    assert "p.sale_price" not in product_query.lower()
