from fastapi.testclient import TestClient

from backend.app.api import app


client = TestClient(app)


def test_marketplaces_endpoint_exposes_independent_site_configuration():
    response = client.get("/api/marketplaces")

    assert response.status_code == 200
    payload = response.json()
    assert {item["code"] for item in payload} == {"US", "AU"}
    assert next(item for item in payload if item["code"] == "US")["currency"] == "USD"
    assert next(item for item in payload if item["code"] == "AU")["currency"] == "AUD"


def test_profit_endpoint_returns_scenario_profit():
    response = client.post(
        "/api/profit/calculate",
        json={"price": "100", "purchase_cost": "30", "platform_fee": "15"},
    )

    assert response.status_code == 200
    assert response.json()["profit"] == "55.00"
    assert response.json()["is_scenario"] is True


def test_scoring_endpoint_requires_sales_metric_type_and_returns_confidence():
    response = client.post(
        "/api/scoring/evaluate",
        json={
            "snapshot": {
                "marketplace_code": "AU",
                "asin": "B000000003",
                "sales_metric_type": "proxy",
                "source": "csv",
            },
            "components": {"demand": "0.8", "trend": None, "profit": "0.7", "competition": "0.6", "risk": "0.9"},
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] == "0.73"
    assert response.json()["confidence"] == "0.80"
    assert response.json()["missing_components"] == ["trend"]


def test_source_status_does_not_echo_secrets():
    response = client.get("/api/system/source-status")

    assert response.status_code == 200
    assert "api_key" not in response.text.lower()
    assert {item["source"] for item in response.json()} == {"keepa", "sp_api", "csv"}


def test_research_task_lifecycle_is_explicitly_visible():
    response = client.post("/api/research/tasks", json={"marketplace": "AU", "keywords": ["yoga mat"]})

    assert response.status_code == 202
    task = response.json()
    assert task["marketplace"] == "AU"
    assert task["status"] == "queued"
    assert client.get(f"/api/research/tasks/{task['task_id']}").json()["status"] == "queued"
