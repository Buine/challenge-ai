from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.enums import IssueType, PaymentStatus, Severity
from app.models import PaymentConfirmation, ReconciliationIssue, SettlementRecord, VoucherRecord
from app.rules.amount_mismatch import detect_amount_mismatch
from app.rules.orphaned import detect_orphaned_payments
from app.rules.post_expiration import detect_post_expiration_payments
from app.rules.stuck_pending import detect_stuck_pending
from app.rules.zombie import detect_zombie_completions


def make_voucher(
    transaction_id: str = "TXN-001",
    amount: Decimal = Decimal("500.00"),
    currency: str = "MXN",
    payment_method: str = "OXXO",
    status: str = PaymentStatus.PENDING,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> VoucherRecord:
    return VoucherRecord(
        transaction_id=transaction_id,
        amount=amount,
        currency=currency,
        payment_method=payment_method,
        status=status,
        source_system="voucher_system",
        created_at=created_at or datetime(2026, 1, 1, 12, 0, 0),
        expires_at=expires_at,
    )


def make_payment(
    transaction_id: str = "TXN-001",
    amount: Decimal = Decimal("500.00"),
    currency: str = "MXN",
    payment_method: str = "OXXO",
    status: str = PaymentStatus.CONFIRMED,
    paid_at: datetime | None = None,
) -> PaymentConfirmation:
    return PaymentConfirmation(
        transaction_id=transaction_id,
        amount=amount,
        currency=currency,
        payment_method=payment_method,
        status=status,
        source_system="payment_processor",
        paid_at=paid_at or datetime(2026, 1, 1, 14, 0, 0),
    )


def make_settlement(
    transaction_id: str = "TXN-001",
    amount: Decimal = Decimal("500.00"),
    currency: str = "MXN",
    status: str = PaymentStatus.COMPLETED,
    settled_at: datetime | None = None,
) -> SettlementRecord:
    return SettlementRecord(
        transaction_id=transaction_id,
        amount=amount,
        currency=currency,
        status=status,
        source_system="settlement_system",
        settled_at=settled_at or datetime(2026, 1, 2, 12, 0, 0),
    )


class TestOrphanedPayments:
    def test_payment_without_voucher_detected_as_high(self):
        payment = make_payment(transaction_id="TXN-ORPHAN")
        issues = detect_orphaned_payments([payment], set())

        assert len(issues) == 1
        assert issues[0].transaction_id == "TXN-ORPHAN"
        assert issues[0].issue_type == IssueType.ORPHANED_PAYMENT
        assert issues[0].severity == Severity.HIGH
        assert issues[0].amount_at_risk == Decimal("500.00")
        assert issues[0].payment_method == "OXXO"
        assert issues[0].currency == "MXN"

    def test_payment_with_matching_voucher_not_flagged(self):
        payment = make_payment(transaction_id="TXN-001")
        issues = detect_orphaned_payments([payment], {"TXN-001"})

        assert len(issues) == 0

    def test_multiple_orphaned_in_single_batch(self):
        payments = [
            make_payment(transaction_id="TXN-A"),
            make_payment(transaction_id="TXN-B"),
            make_payment(transaction_id="TXN-C"),
        ]
        issues = detect_orphaned_payments(payments, {"TXN-OTHER"})

        assert len(issues) == 3
        flagged_ids = {i.transaction_id for i in issues}
        assert flagged_ids == {"TXN-A", "TXN-B", "TXN-C"}

    def test_empty_payments_list(self):
        issues = detect_orphaned_payments([], {"TXN-001"})

        assert len(issues) == 0

    def test_mixed_orphaned_and_matched(self):
        payments = [
            make_payment(transaction_id="TXN-MATCHED"),
            make_payment(transaction_id="TXN-ORPHAN"),
        ]
        issues = detect_orphaned_payments(payments, {"TXN-MATCHED"})

        assert len(issues) == 1
        assert issues[0].transaction_id == "TXN-ORPHAN"

    def test_payment_id_substring_of_voucher_id_still_orphaned(self):
        payment = make_payment(transaction_id="TXN-10")
        issues = detect_orphaned_payments([payment], {"TXN-100", "TXN-1000"})

        assert len(issues) == 1
        assert issues[0].transaction_id == "TXN-10"

    def test_orphaned_payment_amount_at_risk_matches_payment_amount(self):
        payment = make_payment(transaction_id="TXN-ORPHAN", amount=Decimal("1234.56"))
        issues = detect_orphaned_payments([payment], set())

        assert issues[0].amount_at_risk == Decimal("1234.56")

    def test_orphaned_payment_description_contains_transaction_id(self):
        payment = make_payment(transaction_id="TXN-DESC")
        issues = detect_orphaned_payments([payment], set())

        assert "TXN-DESC" in issues[0].description


class TestStuckPending:
    def test_73h_pending_no_confirmation_medium(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=73)
        voucher = make_voucher(transaction_id="TXN-STUCK", created_at=created)
        issues = detect_stuck_pending([voucher], set(), now)

        assert len(issues) == 1
        assert issues[0].severity == Severity.MEDIUM
        assert issues[0].issue_type == IssueType.STUCK_PENDING

    def test_121h_pending_high_severity(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=121)
        voucher = make_voucher(transaction_id="TXN-STUCK-HIGH", created_at=created)
        issues = detect_stuck_pending([voucher], set(), now)

        assert len(issues) == 1
        assert issues[0].severity == Severity.HIGH

    def test_71h_pending_not_flagged(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=71)
        voucher = make_voucher(created_at=created)
        issues = detect_stuck_pending([voucher], set(), now)

        assert len(issues) == 0

    def test_pending_with_confirmation_not_flagged(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=100)
        voucher = make_voucher(transaction_id="TXN-CONFIRMED", created_at=created)
        issues = detect_stuck_pending([voucher], {"TXN-CONFIRMED"}, now)

        assert len(issues) == 0

    def test_paid_status_not_flagged(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=100)
        voucher = make_voucher(status=PaymentStatus.PAID, created_at=created)
        issues = detect_stuck_pending([voucher], set(), now)

        assert len(issues) == 0

    def test_cancelled_status_not_flagged(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=100)
        voucher = make_voucher(status=PaymentStatus.CANCELLED, created_at=created)
        issues = detect_stuck_pending([voucher], set(), now)

        assert len(issues) == 0

    def test_expired_status_not_flagged(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=100)
        voucher = make_voucher(status=PaymentStatus.EXPIRED, created_at=created)
        issues = detect_stuck_pending([voucher], set(), now)

        assert len(issues) == 0

    def test_boundary_exactly_72h_not_flagged(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=72)
        voucher = make_voucher(created_at=created)
        issues = detect_stuck_pending([voucher], set(), now)

        assert len(issues) == 0

    def test_boundary_72h_plus_one_second_flagged(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=72, seconds=1)
        voucher = make_voucher(created_at=created)
        issues = detect_stuck_pending([voucher], set(), now)

        assert len(issues) == 1
        assert issues[0].severity == Severity.MEDIUM

    def test_boundary_exactly_120h_still_medium(self):
        created = datetime(2026, 1, 1, 0, 0, 0)
        now = created + timedelta(hours=120)
        voucher = make_voucher(created_at=created)
        issues = detect_stuck_pending([voucher], set(), now)

        assert len(issues) == 1
        assert issues[0].severity == Severity.MEDIUM


class TestAmountMismatch:
    def test_currency_mismatch_high_severity(self):
        voucher = make_voucher(amount=Decimal("500.00"), currency="MXN")
        payment = make_payment(amount=Decimal("500.00"), currency="COP")
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].severity == Severity.HIGH
        assert "currency mismatch" in issues[0].description.lower()

    def test_same_currency_2_percent_diff_low(self):
        voucher = make_voucher(amount=Decimal("100.00"))
        payment = make_payment(amount=Decimal("102.00"))
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].severity == Severity.LOW

    def test_same_currency_7_percent_diff_medium(self):
        voucher = make_voucher(amount=Decimal("100.00"))
        payment = make_payment(amount=Decimal("107.00"))
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].severity == Severity.MEDIUM

    def test_same_currency_15_percent_diff_high(self):
        voucher = make_voucher(amount=Decimal("100.00"))
        payment = make_payment(amount=Decimal("115.00"))
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].severity == Severity.HIGH

    def test_0_5_percent_diff_not_flagged(self):
        voucher = make_voucher(amount=Decimal("1000.00"))
        payment = make_payment(amount=Decimal("1005.00"))
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 0

    @pytest.mark.parametrize(
        "voucher_amount,payment_amount,expected_flagged",
        [
            (Decimal("100.00"), Decimal("101.00"), False),
            (Decimal("100.00"), Decimal("101.01"), True),
            (Decimal("100.00"), Decimal("101.02"), True),
        ],
        ids=[
            "exactly_1_percent_not_flagged",
            "1.01_percent_flagged",
            "1.02_percent_flagged",
        ],
    )
    def test_boundary_positive_tolerance(self, voucher_amount, payment_amount, expected_flagged):
        voucher = make_voucher(amount=voucher_amount)
        payment = make_payment(amount=payment_amount)
        issues = detect_amount_mismatch([(voucher, payment)])

        assert (len(issues) > 0) == expected_flagged

    @pytest.mark.parametrize(
        "voucher_amount,payment_amount,expected_flagged",
        [
            (Decimal("100.00"), Decimal("99.00"), False),
            (Decimal("100.00"), Decimal("98.99"), True),
            (Decimal("100.00"), Decimal("98.98"), True),
        ],
        ids=[
            "exactly_neg_1_percent_not_flagged",
            "neg_1.01_percent_flagged",
            "neg_1.02_percent_flagged",
        ],
    )
    def test_boundary_negative_tolerance(self, voucher_amount, payment_amount, expected_flagged):
        voucher = make_voucher(amount=voucher_amount)
        payment = make_payment(amount=payment_amount)
        issues = detect_amount_mismatch([(voucher, payment)])

        assert (len(issues) > 0) == expected_flagged

    def test_cop_large_amounts(self):
        voucher = make_voucher(
            amount=Decimal("350000.00"), currency="COP", payment_method="EFECTY"
        )
        payment = make_payment(
            amount=Decimal("357000.00"), currency="COP", payment_method="EFECTY"
        )
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].severity == Severity.LOW
        assert issues[0].currency == "COP"

    def test_zero_voucher_amount_skipped(self):
        voucher = make_voucher(amount=Decimal("0"))
        payment = make_payment(amount=Decimal("100.00"))
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 0

    def test_amount_at_risk_equals_absolute_difference(self):
        voucher = make_voucher(amount=Decimal("200.00"))
        payment = make_payment(amount=Decimal("230.00"))
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].amount_at_risk == Decimal("30.00")

    def test_amount_at_risk_when_payment_less_than_voucher(self):
        voucher = make_voucher(amount=Decimal("200.00"))
        payment = make_payment(amount=Decimal("170.00"))
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].amount_at_risk == Decimal("30.00")

    def test_exact_match_not_flagged(self):
        voucher = make_voucher(amount=Decimal("500.00"))
        payment = make_payment(amount=Decimal("500.00"))
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 0

    def test_uses_decimal_precision_not_float(self):
        voucher = make_voucher(amount=Decimal("100.00"))
        payment = make_payment(amount=Decimal("100.10"))
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 0
        assert isinstance(voucher.amount, Decimal)
        assert isinstance(payment.amount, Decimal)

    def test_currency_mismatch_amount_at_risk_is_payment_amount(self):
        voucher = make_voucher(amount=Decimal("500.00"), currency="MXN")
        payment = make_payment(amount=Decimal("120000.00"), currency="COP")
        issues = detect_amount_mismatch([(voucher, payment)])

        assert issues[0].amount_at_risk == Decimal("120000.00")

    @pytest.mark.parametrize(
        "pct_diff,expected_severity",
        [
            (Decimal("0.02"), Severity.LOW),
            (Decimal("0.05"), Severity.LOW),
            (Decimal("0.0501"), Severity.MEDIUM),
            (Decimal("0.10"), Severity.MEDIUM),
            (Decimal("0.1001"), Severity.HIGH),
        ],
        ids=[
            "2_pct_low",
            "5_pct_boundary_low",
            "5.01_pct_medium",
            "10_pct_boundary_medium",
            "10.01_pct_high",
        ],
    )
    def test_severity_thresholds(self, pct_diff, expected_severity):
        base = Decimal("10000.00")
        payment_amount = base + (base * pct_diff).quantize(Decimal("0.01"))
        voucher = make_voucher(amount=base)
        payment = make_payment(amount=payment_amount)
        issues = detect_amount_mismatch([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].severity == expected_severity


class TestZombieCompletions:
    def test_completed_without_confirmed_payment_detected(self):
        settlement = make_settlement(transaction_id="TXN-ZOMBIE")
        issues = detect_zombie_completions([settlement], set())

        assert len(issues) == 1
        assert issues[0].transaction_id == "TXN-ZOMBIE"
        assert issues[0].issue_type == IssueType.ZOMBIE_COMPLETION
        assert issues[0].severity == Severity.HIGH

    def test_full_lifecycle_with_confirmed_not_flagged(self):
        settlement = make_settlement(transaction_id="TXN-OK")
        issues = detect_zombie_completions([settlement], {"TXN-OK"})

        assert len(issues) == 0

    def test_non_completed_settlement_not_flagged(self):
        settlement = make_settlement(transaction_id="TXN-PENDING", status=PaymentStatus.PENDING)
        issues = detect_zombie_completions([settlement], set())

        assert len(issues) == 0

    def test_multiple_zombies_in_batch(self):
        settlements = [
            make_settlement(transaction_id="TXN-Z1"),
            make_settlement(transaction_id="TXN-Z2"),
            make_settlement(transaction_id="TXN-Z3"),
        ]
        issues = detect_zombie_completions(settlements, set())

        assert len(issues) == 3
        flagged_ids = {i.transaction_id for i in issues}
        assert flagged_ids == {"TXN-Z1", "TXN-Z2", "TXN-Z3"}

    def test_payment_exists_but_pending_not_confirmed_still_zombie(self):
        settlement = make_settlement(transaction_id="TXN-PEND-ONLY")
        confirmed_ids: set[str] = set()
        issues = detect_zombie_completions([settlement], confirmed_ids)

        assert len(issues) == 1
        assert issues[0].transaction_id == "TXN-PEND-ONLY"

    def test_zombie_amount_at_risk_matches_settlement_amount(self):
        settlement = make_settlement(
            transaction_id="TXN-ZOMBIE", amount=Decimal("9999.99")
        )
        issues = detect_zombie_completions([settlement], set())

        assert issues[0].amount_at_risk == Decimal("9999.99")

    def test_zombie_currency_matches_settlement(self):
        settlement = make_settlement(transaction_id="TXN-ZOMBIE", currency="COP")
        issues = detect_zombie_completions([settlement], set())

        assert issues[0].currency == "COP"

    def test_mixed_completed_and_other_statuses(self):
        settlements = [
            make_settlement(transaction_id="TXN-C1", status=PaymentStatus.COMPLETED),
            make_settlement(transaction_id="TXN-P1", status=PaymentStatus.PAID),
            make_settlement(transaction_id="TXN-C2", status=PaymentStatus.COMPLETED),
        ]
        issues = detect_zombie_completions(settlements, {"TXN-C1"})

        assert len(issues) == 1
        assert issues[0].transaction_id == "TXN-C2"

    def test_zombie_resolves_payment_method_from_voucher_map(self):
        settlement = make_settlement(transaction_id="TXN-Z-PM")
        voucher = make_voucher(transaction_id="TXN-Z-PM", payment_method="EFECTY")
        voucher_map = {"TXN-Z-PM": voucher}
        issues = detect_zombie_completions([settlement], set(), voucher_map)

        assert len(issues) == 1
        assert issues[0].payment_method == "EFECTY"

    def test_zombie_without_voucher_map_has_none_payment_method(self):
        settlement = make_settlement(transaction_id="TXN-Z-NO-V")
        issues = detect_zombie_completions([settlement], set())

        assert len(issues) == 1
        assert issues[0].payment_method is None


class TestPostExpirationPayments:
    def test_payment_1_minute_after_expiry_detected(self):
        expires = datetime(2026, 1, 2, 0, 0, 0)
        paid = expires + timedelta(minutes=1)
        voucher = make_voucher(transaction_id="TXN-POST", expires_at=expires)
        payment = make_payment(transaction_id="TXN-POST", paid_at=paid)
        issues = detect_post_expiration_payments([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].transaction_id == "TXN-POST"
        assert issues[0].issue_type == IssueType.POST_EXPIRATION_PAYMENT
        assert issues[0].severity == Severity.HIGH

    def test_payment_1_minute_before_expiry_not_flagged(self):
        expires = datetime(2026, 1, 2, 0, 0, 0)
        paid = expires - timedelta(minutes=1)
        voucher = make_voucher(expires_at=expires)
        payment = make_payment(paid_at=paid)
        issues = detect_post_expiration_payments([(voucher, payment)])

        assert len(issues) == 0

    def test_boundary_exactly_at_expiration_not_flagged(self):
        expires = datetime(2026, 1, 2, 0, 0, 0)
        voucher = make_voucher(expires_at=expires)
        payment = make_payment(paid_at=expires)
        issues = detect_post_expiration_payments([(voucher, payment)])

        assert len(issues) == 0

    def test_boundary_1_second_after_expiration_flagged(self):
        expires = datetime(2026, 1, 2, 0, 0, 0)
        paid = expires + timedelta(seconds=1)
        voucher = make_voucher(expires_at=expires)
        payment = make_payment(paid_at=paid)
        issues = detect_post_expiration_payments([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].severity == Severity.HIGH

    def test_oxxo_48h_window_scenario(self):
        created = datetime(2026, 1, 1, 10, 0, 0)
        expires = created + timedelta(hours=48)
        paid = expires + timedelta(hours=2)
        voucher = make_voucher(
            transaction_id="TXN-OXXO-LATE",
            payment_method="OXXO",
            created_at=created,
            expires_at=expires,
        )
        payment = make_payment(
            transaction_id="TXN-OXXO-LATE",
            payment_method="OXXO",
            paid_at=paid,
        )
        issues = detect_post_expiration_payments([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].payment_method == "OXXO"
        assert issues[0].transaction_id == "TXN-OXXO-LATE"

    def test_efecty_72h_window_scenario(self):
        created = datetime(2026, 1, 1, 8, 0, 0)
        expires = created + timedelta(hours=72)
        paid = expires + timedelta(hours=1)
        voucher = make_voucher(
            transaction_id="TXN-EFECTY-LATE",
            payment_method="EFECTY",
            currency="COP",
            created_at=created,
            expires_at=expires,
        )
        payment = make_payment(
            transaction_id="TXN-EFECTY-LATE",
            payment_method="EFECTY",
            currency="COP",
            paid_at=paid,
        )
        issues = detect_post_expiration_payments([(voucher, payment)])

        assert len(issues) == 1
        assert issues[0].payment_method == "EFECTY"
        assert issues[0].currency == "COP"

    def test_no_expiry_set_on_voucher_not_flagged(self):
        voucher = make_voucher(expires_at=None)
        payment = make_payment(paid_at=datetime(2026, 6, 1, 0, 0, 0))
        issues = detect_post_expiration_payments([(voucher, payment)])

        assert len(issues) == 0

    def test_post_expiration_amount_at_risk_is_payment_amount(self):
        expires = datetime(2026, 1, 2, 0, 0, 0)
        paid = expires + timedelta(hours=1)
        voucher = make_voucher(
            amount=Decimal("300.00"),
            expires_at=expires,
        )
        payment = make_payment(
            amount=Decimal("300.00"),
            paid_at=paid,
        )
        issues = detect_post_expiration_payments([(voucher, payment)])

        assert issues[0].amount_at_risk == Decimal("300.00")

    def test_description_contains_timestamps(self):
        expires = datetime(2026, 1, 2, 0, 0, 0)
        paid = expires + timedelta(hours=5)
        voucher = make_voucher(transaction_id="TXN-TS", expires_at=expires)
        payment = make_payment(transaction_id="TXN-TS", paid_at=paid)
        issues = detect_post_expiration_payments([(voucher, payment)])

        assert expires.isoformat() in issues[0].description
        assert paid.isoformat() in issues[0].description

    def test_multiple_pairs_mixed_results(self):
        expires = datetime(2026, 1, 2, 0, 0, 0)
        pairs = [
            (
                make_voucher(transaction_id="TXN-OK", expires_at=expires),
                make_payment(
                    transaction_id="TXN-OK",
                    paid_at=expires - timedelta(hours=1),
                ),
            ),
            (
                make_voucher(transaction_id="TXN-LATE", expires_at=expires),
                make_payment(
                    transaction_id="TXN-LATE",
                    paid_at=expires + timedelta(hours=1),
                ),
            ),
            (
                make_voucher(transaction_id="TXN-NOEXP", expires_at=None),
                make_payment(transaction_id="TXN-NOEXP"),
            ),
        ]
        issues = detect_post_expiration_payments(pairs)

        assert len(issues) == 1
        assert issues[0].transaction_id == "TXN-LATE"
