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
