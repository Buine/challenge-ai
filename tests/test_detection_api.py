def _make_voucher(transaction_id, amount="100.00", status="PENDING", created_at="2025-01-01T10:00:00"):
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": "MXN",
        "payment_method": "OXXO",
        "status": status,
        "source_system": "voucher_system",
        "created_at": created_at,
    }


def _make_payment(transaction_id, amount="100.00", status="CONFIRMED", paid_at="2025-01-01T14:00:00"):
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": "MXN",
        "payment_method": "OXXO",
        "status": status,
        "source_system": "payment_processor",
        "paid_at": paid_at,
    }


class TestDetectionRun:
    def test_detection_run_returns_issues(self, client):
        client.post(
            "/api/v1/ingest/payments",
            json=[_make_payment("TXN-DET-ORPHAN-001")],
        )

        response = client.post("/api/v1/detection/run")

        assert response.status_code == 200
        data = response.json()
        assert data["new_issues_found"] >= 1
        assert "ORPHANED_PAYMENT" in data["issues_by_type"]

    def test_detection_run_twice_is_idempotent(self, client):
        client.post(
            "/api/v1/ingest/payments",
            json=[_make_payment("TXN-DET-IDEM-001")],
        )

        first_run = client.post("/api/v1/detection/run").json()
        second_run = client.post("/api/v1/detection/run").json()

        assert first_run["new_issues_found"] == second_run["new_issues_found"]
        assert second_run["previous_issues_cleared"] == first_run["new_issues_found"]

    def test_detection_reflects_updated_data(self, client):
        client.post(
            "/api/v1/ingest/payments",
            json=[_make_payment("TXN-DET-UPD-001")],
        )
        first_run = client.post("/api/v1/detection/run").json()

        client.post(
            "/api/v1/ingest/payments",
            json=[_make_payment("TXN-DET-UPD-002")],
        )
        second_run = client.post("/api/v1/detection/run").json()

        assert second_run["new_issues_found"] > first_run["new_issues_found"]
