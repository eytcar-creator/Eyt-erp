from api.production.main import app

def test_public_catalog_routes_are_registered():
    paths = {route.path for route in app.routes}
    assert "/api/public/catalog/products" in paths
    assert "/api/public/catalog/products/{sku}" in paths

def test_public_catalog_has_no_write_dependency():
    route = next(r for r in app.routes if r.path == "/api/public/catalog/products")
    assert not route.dependant.dependencies

def test_public_catalog_module_is_read_only():
    source = open("api/production/public_catalog_api.py", encoding="utf-8").read()
    assert "INSERT INTO" not in source
    assert "UPDATE " not in source
    assert "DELETE FROM" not in source
