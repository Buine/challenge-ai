from decimal import Decimal

import pytest


def _make_voucher(
    transaction_id="TXN-001",
    amount="150.00",
    currency="MXN",
    payment_method="OXXO",
    status="PENDING",
    source_system="voucher_system",
    created_at="2025-06-01T10:00:00",
    expires_at=None,
):
    payload = {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "payment_method": payment_method,
        "status": status,
        "source_system": source_system,
        "created_at": created_at,
    }
    if expires_at:
        payload["expires_at"] = expires_at
    return payload


def _make_payment(
    transaction_id="TXN-001",
    amount="150.00",
    currency="MXN",
    payment_method="OXXO",
    status="CONFIRMED",
    source_system="payment_processor",
    paid_at="2025-06-01T12:00:00",
):
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "payment_method": payment_method,
        "status": status,
        "source_system": source_system,
        "paid_at": paid_at,
    }


def _make_settlement(
    transaction_id="TXN-001",
    amount="150.00",
    currency="MXN",
    status="COMPLETED",
    source_system="bank_settlement",
    settled_at="2025-06-02T08:00:00",
):
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "status": status,
        "source_system": source_system,
        "settled_at": settled_at,
    }


class TestIngestVouchers:
    def test_valid_voucher_returns_201_with_correct_created_count(self, client):
        response = client.post("/api/v1/ingest/vouchers", json=[_make_voucher()])

        assert response.status_code == 201
        data = response.json()
        assert data["received"] == 1
        assert data["created"] == 1
        assert data["duplicates"] == 0

    def test_duplicate_transaction_id_is_skipped(self, client):
        voucher = _make_voucher(transaction_id="TXN-DUP-001")
        client.post("/api/v1/ingest/vouchers", json=[voucher])

        response = client.post("/api/v1/ingest/vouchers", json=[voucher])

        assert response.status_code == 201
        data = response.json()
        assert data["received"] == 1
        assert data["created"] == 0
        assert data["duplicates"] == 1

    def test_empty_list_returns_201_with_zero_created(self, client):
        response = client.post("/api/v1/ingest/vouchers", json=[])

        assert response.status_code == 201
        data = response.json()
        assert data["received"] == 0
        assert data["created"] == 0
        assert data["duplicates"] == 0

    def test_multiple_vouchers_in_single_batch(self, client):
        vouchers = [
            _make_voucher(transaction_id="TXN-BATCH-001"),
            _make_voucher(transaction_id="TXN-BATCH-002"),
            _make_voucher(transaction_id="TXN-BATCH-003"),
        ]

        response = client.post("/api/v1/ingest/vouchers", json=vouchers)

        assert response.status_code == 201
        data = response.json()
        assert data["received"] == 3
        assert data["created"] == 3
        assert data["duplicates"] == 0

    def test_invalid_voucher_data_returns_422(self, client):
        invalid_payload = [{"transaction_id": "TXN-BAD"}]

        response = client.post("/api/v1/ingest/vouchers", json=invalid_payload)

        assert response.status_code == 422


class TestIngestPayments:
    def test_valid_payment_returns_201(self, client):
        response = client.post("/api/v1/ingest/payments", json=[_make_payment()])

        assert response.status_code == 201
        data = response.json()
        assert data["received"] == 1
        assert data["created"] == 1
        assert data["duplicates"] == 0

    def test_invalid_payment_data_returns_422(self, client):
        invalid_payload = [{"amount": "not_a_number"}]

        response = client.post("/api/v1/ingest/payments", json=invalid_payload)

        assert response.status_code == 422


class TestIngestSettlements:
    def test_valid_settlement_returns_201(self, client):
        response = client.post("/api/v1/ingest/settlements", json=[_make_settlement()])

        assert response.status_code == 201
        data = response.json()
        assert data["received"] == 1
        assert data["created"] == 1
        assert data["duplicates"] == 0
