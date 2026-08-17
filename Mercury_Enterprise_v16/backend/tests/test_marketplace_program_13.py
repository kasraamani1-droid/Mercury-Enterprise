"""Program 13 — Mercury Digital Marketplace tests."""

from __future__ import annotations

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_marketplace_overview_and_catalog():
    login_as("operator")
    overview = client.get("/api/v1/marketplace/overview")
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["sellers"] >= 5
    assert body["products"] >= 8
    assert body["listings"] >= 8
    assert body["categories"] >= 20
    cats = client.get("/api/v1/marketplace/categories")
    assert cats.status_code == 200
    codes = {c["code"] for c in cats.json()}
    for required in (
        "aircraft_parts",
        "rotables",
        "calibration",
        "avionics_repairs",
        "training",
        "jobs",
        "software",
    ):
        assert required in codes


def test_sellers_products_search_cart_quote_order_review():
    login_as("operator")
    sellers = client.get("/api/v1/marketplace/sellers")
    assert sellers.status_code == 200
    assert len(sellers.json()) >= 5
    seller = sellers.json()[0]
    assert "verification_disclaimer" in seller
    assert "regulatory" in seller["verification_disclaimer"].lower() or "not regulatory" in seller[
        "verification_disclaimer"
    ].lower()

    products = client.get("/api/v1/marketplace/products")
    assert products.status_code == 200
    assert len(products.json()) >= 8
    product = products.json()[0]
    pid = product["id"]

    search = client.get("/api/v1/marketplace/search", params={"q": "torque"})
    assert search.status_code == 200
    assert search.json()["total"] >= 1

    pricing = client.get(f"/api/v1/marketplace/products/{pid}/pricing")
    assert pricing.status_code == 200
    assert "unit_price" in pricing.json()

    inventory = client.get(f"/api/v1/marketplace/products/{pid}/inventory")
    assert inventory.status_code == 200
    assert "qty_available" in inventory.json()

    cart = client.post("/api/v1/marketplace/cart", json={"product_id": pid, "qty": 2})
    assert cart.status_code == 201, cart.text
    assert client.get("/api/v1/marketplace/cart").status_code == 200

    quote = client.post("/api/v1/marketplace/quotes", json={"product_id": pid, "qty": 2})
    assert quote.status_code == 201, quote.text
    qid = quote.json()["id"]

    order = client.post("/api/v1/marketplace/orders", json={"quote_id": qid})
    assert order.status_code == 201, order.text
    assert order.json()["payment_status"] == "not_configured"
    assert len(order.json()["lines"]) == 1

    fav = client.post("/api/v1/marketplace/favorites", json={"product_id": pid})
    assert fav.status_code == 201
    review = client.post(
        "/api/v1/marketplace/reviews",
        json={"product_id": pid, "rating": 5, "title": "Solid", "body": "Demo review"},
    )
    assert review.status_code == 201, review.text
    saved = client.post(
        "/api/v1/marketplace/saved-searches",
        json={"name": "Torque tools", "query_json": '{"q":"torque"}'},
    )
    assert saved.status_code == 201


def test_legacy_listings_still_work():
    login_as("operator")
    listings = client.get("/api/v1/marketplace/listings")
    assert listings.status_code == 200
    assert len(listings.json()) >= 8
    code = f"P13-DEMO-{__import__('uuid').uuid4().hex[:8].upper()}"
    created = client.post(
        "/api/v1/marketplace/listings",
        json={
            "listing_type": "parts",
            "code": code,
            "title": "Program 13 demo nut",
            "supplier_name": "Demo",
        },
    )
    assert created.status_code == 201, created.text


def test_marketplace_rbac_and_tenant_isolation():
    login_as("viewer")
    assert client.get("/api/v1/marketplace/overview").status_code == 200
    assert (
        client.post(
            "/api/v1/marketplace/sellers",
            json={"seller_type": "consultant", "legal_name": "Nope LLC"},
        ).status_code
        == 403
    )
    login_as("operator")
    assert (
        client.get("/api/v1/marketplace/sellers", params={"organization_id": "org-aviation-west"}).status_code
        == 403
    )
