from decimal import Decimal


def _make_voucher(transaction_id, amount="100.00", payment_method="OXXO", currency="MXN",
                  status="PENDING", created_at="2025-01-01T10:00:00", expires_at=None):
    payload = {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "payment_method": payment_method,
        "status": status,
        "source_system": "voucher_system",
        "created_at": created_at,
    }
    if expires_at:
        payload["expires_at"] = expires_at
    return payload


def _make_payment(transaction_id, amount="100.00", payment_method="OXXO", currency="MXN",
                  status="CONFIRMED", paid_at="2025-01-01T14:00:00"):
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "payment_method": payment_method,
        "status": status,
        "source_system": "payment_processor",
        "paid_at": paid_at,
    }


def _make_settlement(transaction_id, amount="100.00", currency="MXN", status="COMPLETED",
                     settled_at="2025-01-02T08:00:00"):
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "status": status,
        "source_system": "bank_settlement",
        "settled_at": settled_at,
    }


def _seed_diverse_issues(client):
    client.post("/api/v1/ingest/payments", json=[
        _make_payment("TXN-ISS-ORPH-001", payment_method="OXXO"),
        _make_payment("TXN-ISS-ORPH-002", payment_method="EFECTY", currency="COP"),
    ])

    client.post("/api/v1/ingest/vouchers", json=[
        _make_voucher("TXN-ISS-MISMATCH-001", amount="100.00"),
    ])
    client.post("/api/v1/ingest/payments", json=[
        _make_payment("TXN-ISS-MISMATCH-001", amount="200.00"),
    ])

    client.post("/api/v1/ingest/settlements", json=[
        _make_settlement("TXN-ISS-ZOMBIE-001"),
    ])

    client.post("/api/v1/detection/run")


class TestIssuesFiltering:
    def test_filter_by_issue_type(self, client):
        _seed_diverse_issues(client)

        response = client.get("/api/v1/issues", params={"issue_type": "ORPHANED_PAYMENT"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["issue_type"] == "ORPHANED_PAYMENT"

    def test_filter_by_severity(self, client):
        _seed_diverse_issues(client)

        response = client.get("/api/v1/issues", params={"severity": "HIGH"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["severity"] == "HIGH"

    def test_filter_by_payment_method(self, client):
        _seed_diverse_issues(client)

        response = client.get("/api/v1/issues", params={"payment_method": "EFECTY"})

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["payment_method"] == "EFECTY"

    def test_combined_filters(self, client):
        _seed_diverse_issues(client)

        response = client.get("/api/v1/issues", params={
            "issue_type": "ORPHANED_PAYMENT",
            "severity": "HIGH",
            "payment_method": "OXXO",
        })

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["issue_type"] == "ORPHANED_PAYMENT"
            assert item["severity"] == "HIGH"
            assert item["payment_method"] == "OXXO"

    def test_pagination_with_offset_and_limit(self, client):
        _seed_diverse_issues(client)

        full_response = client.get("/api/v1/issues", params={"limit": 50, "offset": 0})
        full_data = full_response.json()
        total = full_data["total"]

        page_response = client.get("/api/v1/issues", params={"limit": 1, "offset": 0})
        page_data = page_response.json()

        assert page_data["limit"] == 1
        assert page_data["offset"] == 0
        assert len(page_data["items"]) <= 1
        assert page_data["total"] == total

    def test_pagination_second_page_returns_different_items(self, client):
        _seed_diverse_issues(client)

        page1 = client.get("/api/v1/issues", params={"limit": 1, "offset": 0}).json()
        page2 = client.get("/api/v1/issues", params={"limit": 1, "offset": 1}).json()

        if page1["total"] > 1:
            assert page1["items"][0]["id"] != page2["items"][0]["id"]

    def test_empty_results_with_nonexistent_filter(self, client):
        _seed_diverse_issues(client)

        response = client.get("/api/v1/issues", params={"issue_type": "NONEXISTENT_TYPE"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestIssuesSummary:
    def test_summary_returns_correct_counts_by_type(self, client):
        _seed_diverse_issues(client)

        response = client.get("/api/v1/issues/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_issues"] > 0
        assert isinstance(data["issues_by_type"], dict)
        assert sum(data["issues_by_type"].values()) == data["total_issues"]

    def test_summary_amount_at_risk_calculation(self, client):
        _seed_diverse_issues(client)

        response = client.get("/api/v1/issues/summary")

        data = response.json()
        assert Decimal(str(data["total_amount_at_risk"])) > 0

    def test_summary_percentage_of_transactions_with_issues(self, client):
        _seed_diverse_issues(client)

        response = client.get("/api/v1/issues/summary")

        data = response.json()
        assert data["total_transactions"] > 0
        assert data["transactions_with_issues"] > 0
        assert Decimal(str(data["issue_rate_percent"])) > 0
        assert Decimal(str(data["issue_rate_percent"])) <= 100

    def test_summary_issues_by_severity_present(self, client):
        _seed_diverse_issues(client)

        response = client.get("/api/v1/issues/summary")

        data = response.json()
        assert isinstance(data["issues_by_severity"], dict)
        assert sum(data["issues_by_severity"].values()) == data["total_issues"]

    def test_summary_with_no_issues_returns_zero_values(self, client):
        response = client.get("/api/v1/issues/summary")

        data = response.json()
        assert data["total_issues"] == 0
        assert Decimal(str(data["total_amount_at_risk"])) == 0
        assert data["transactions_with_issues"] == 0
