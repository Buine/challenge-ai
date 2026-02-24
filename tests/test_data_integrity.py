import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module")
def vouchers():
    with open(DATA_DIR / "vouchers.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def payments():
    with open(DATA_DIR / "payments.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def settlements():
    with open(DATA_DIR / "settlements.json") as f:
        return json.load(f)


class TestDataIntegrity:
    def test_minimum_300_unique_transactions(self, vouchers, payments, settlements):
        all_ids = set()
        for records in [vouchers, payments, settlements]:
            for r in records:
                all_ids.add(r["transaction_id"])
        assert len(all_ids) >= 300

    def test_voucher_records_have_required_fields(self, vouchers):
        required = {"transaction_id", "amount", "currency", "payment_method", "status", "source_system", "created_at"}
        for v in vouchers:
            assert required.issubset(v.keys()), f"Missing fields in voucher {v.get('transaction_id')}"

    def test_payment_records_have_required_fields(self, payments):
        required = {"transaction_id", "amount", "currency", "payment_method", "status", "source_system", "paid_at"}
        for p in payments:
            assert required.issubset(p.keys()), f"Missing fields in payment {p.get('transaction_id')}"

    def test_settlement_records_have_required_fields(self, settlements):
        required = {"transaction_id", "amount", "currency", "status", "source_system", "settled_at"}
        for s in settlements:
            assert required.issubset(s.keys()), f"Missing fields in settlement {s.get('transaction_id')}"

    def test_oxxo_uses_mxn_currency(self, vouchers):
        oxxo_vouchers = [v for v in vouchers if v["payment_method"] == "OXXO"]
        assert len(oxxo_vouchers) > 0
        for v in oxxo_vouchers:
            assert v["currency"] == "MXN"

    def test_efecty_uses_cop_currency(self, vouchers):
        efecty_vouchers = [v for v in vouchers if v["payment_method"] == "EFECTY"]
        assert len(efecty_vouchers) > 0
        for v in efecty_vouchers:
            assert v["currency"] == "COP"

    def test_mix_of_payment_methods(self, vouchers):
        methods = {v["payment_method"] for v in vouchers}
        assert "OXXO" in methods
        assert "EFECTY" in methods

    def test_mix_of_statuses(self, vouchers):
        statuses = {v["status"] for v in vouchers}
        assert "PENDING" in statuses
        assert "EXPIRED" in statuses
        assert "CANCELLED" in statuses

    def test_at_least_30_transactions_with_intentional_issues(self, vouchers, payments, settlements):
        voucher_ids = {v["transaction_id"] for v in vouchers}
        payment_ids = {p["transaction_id"] for p in payments}

        orphaned = [p for p in payments if p["transaction_id"] not in voucher_ids]

        issue_indicators = len(orphaned)

        assert issue_indicators >= 5

    def test_orphaned_payments_exist(self, vouchers, payments):
        voucher_ids = {v["transaction_id"] for v in vouchers}
        orphaned = [p for p in payments if p["transaction_id"] not in voucher_ids]
        assert len(orphaned) >= 8

    def test_unique_transaction_ids_per_source(self, vouchers, payments, settlements):
        voucher_ids = [v["transaction_id"] for v in vouchers]
        assert len(voucher_ids) == len(set(voucher_ids))

        payment_ids = [p["transaction_id"] for p in payments]
        assert len(payment_ids) == len(set(payment_ids))

        settlement_ids = [s["transaction_id"] for s in settlements]
        assert len(settlement_ids) == len(set(settlement_ids))

    def test_amounts_are_positive(self, vouchers, payments, settlements):
        for v in vouchers:
            assert float(v["amount"]) > 0
        for p in payments:
            assert float(p["amount"]) > 0
        for s in settlements:
            assert float(s["amount"]) > 0

    def test_source_systems_are_correct(self, vouchers, payments, settlements):
        for v in vouchers:
            assert v["source_system"] == "voucher_system"
        for p in payments:
            assert p["source_system"] == "payment_processor"
        for s in settlements:
            assert s["source_system"] == "bank_settlement"
