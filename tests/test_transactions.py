def _make_voucher(
    transaction_id="TXN-VIEW-001",
    amount="200.00",
    currency="MXN",
    payment_method="OXXO",
    status="PENDING",
    created_at="2025-06-01T10:00:00",
    expires_at=None,
):
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


def _make_payment(
    transaction_id="TXN-VIEW-001",
    amount="200.00",
    currency="MXN",
    payment_method="OXXO",
    status="CONFIRMED",
    paid_at="2025-06-01T14:00:00",
):
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "payment_method": payment_method,
        "status": status,
        "source_system": "payment_processor",
        "paid_at": paid_at,
    }


def _make_settlement(
    transaction_id="TXN-VIEW-001",
    amount="200.00",
    currency="MXN",
    status="COMPLETED",
    settled_at="2025-06-02T08:00:00",
):
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "status": status,
        "source_system": "bank_settlement",
        "settled_at": settled_at,
    }


def _ingest_full_lifecycle(client, txn_id="TXN-VIEW-001"):
    client.post("/api/v1/ingest/vouchers", json=[_make_voucher(transaction_id=txn_id)])
    client.post(
        "/api/v1/ingest/payments",
        json=[_make_payment(transaction_id=txn_id)],
    )
    client.post(
        "/api/v1/ingest/settlements",
        json=[_make_settlement(transaction_id=txn_id)],
    )


class TestTransactionView:
    def test_full_lifecycle_returns_complete_transaction_with_source_system(self, client):
        txn_id = "TXN-FULL-001"
        _ingest_full_lifecycle(client, txn_id)

        response = client.get(f"/api/v1/transactions/{txn_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["transaction_id"] == txn_id
        assert data["status"] == "complete"
        assert data["voucher"] is not None
        assert data["voucher"]["source_system"] == "voucher_system"
        assert data["payment"] is not None
        assert data["payment"]["source_system"] == "payment_processor"
        assert data["settlement"] is not None
        assert data["settlement"]["source_system"] == "bank_settlement"

    def test_only_voucher_ingested_returns_partial_view(self, client):
        txn_id = "TXN-PARTIAL-001"
        client.post("/api/v1/ingest/vouchers", json=[_make_voucher(transaction_id=txn_id)])

        response = client.get(f"/api/v1/transactions/{txn_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["transaction_id"] == txn_id
        assert data["status"] == "partial"
        assert data["voucher"] is not None
        assert data["payment"] is None
        assert data["settlement"] is None

    def test_unknown_transaction_id_returns_404(self, client):
        response = client.get("/api/v1/transactions/TXN-NONEXISTENT-999")

        assert response.status_code == 404

    def test_transaction_with_detected_issues_has_populated_issues_array(self, client):
        txn_id = "TXN-ORPHAN-001"
        client.post(
            "/api/v1/ingest/payments",
            json=[_make_payment(transaction_id=txn_id)],
        )
        client.post("/api/v1/detection/run")

        response = client.get(f"/api/v1/transactions/{txn_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["issues"]) > 0
        assert data["issues"][0]["transaction_id"] == txn_id
        assert data["issues"][0]["issue_type"] == "ORPHANED_PAYMENT"

    def test_complete_transaction_without_issues_has_empty_issues_list(self, client):
        txn_id = "TXN-CLEAN-001"
        _ingest_full_lifecycle(client, txn_id)
        client.post("/api/v1/detection/run")

        response = client.get(f"/api/v1/transactions/{txn_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["issues"] == []
