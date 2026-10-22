from fastapi.testclient import TestClient

from backend.app.api import app


client = TestClient(app)


def test_csv_import_normalizes_rows_without_turning_estimates_into_actual_sales():
    csv = "asin,title,price,currency,sales_metric_type,estimated_monthly_sales\nB000000004,Sample mat,29.90,USD,estimated,120\n"
    response = client.post(
        "/api/products/import?marketplace=US",
        files={"file": ("products.csv", csv.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] == 1
    assert payload["rejected"] == 0
    assert payload["items"][0]["sales_metric_type"] == "estimated"
    assert payload["items"][0]["estimated_monthly_sales"] == 120


def test_csv_import_rejects_rows_without_explicit_sales_metric_type():
    csv = "asin,title,price,currency\nB000000005,Missing type,20,USD\n"
    response = client.post(
        "/api/products/import?marketplace=US",
        files={"file": ("products.csv", csv.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] == 0
    assert payload["rejected"] == 1
    assert "sales_metric_type" in payload["errors"][0]["message"]
