from datetime import UTC, datetime
from decimal import Decimal

from app.config import settings
from app.enums import IssueType, Severity
from app.models import PaymentConfirmation, ReconciliationIssue, VoucherRecord


def detect_amount_mismatch(
    pairs: list[tuple[VoucherRecord, PaymentConfirmation]],
) -> list[ReconciliationIssue]:
    issues = []
    tolerance = Decimal(str(settings.amount_mismatch_tolerance))
    medium_threshold = Decimal(str(settings.amount_mismatch_medium_threshold))
    high_threshold = Decimal(str(settings.amount_mismatch_high_threshold))

    for voucher, payment in pairs:
        if voucher.currency != payment.currency:
            issues.append(
                ReconciliationIssue(
                    transaction_id=voucher.transaction_id,
                    issue_type=IssueType.AMOUNT_MISMATCH,
                    severity=Severity.HIGH,
                    detected_at=datetime.now(UTC).replace(tzinfo=None),
                    description=(
                        f"Currency mismatch for transaction {voucher.transaction_id}: "
                        f"voucher in {voucher.currency}, payment in {payment.currency}"
                    ),
                    amount_at_risk=payment.amount,
                    payment_method=voucher.payment_method,
                    currency=voucher.currency,
                    suggested_resolution=(
                        "Review currency configuration. This may indicate a system error "
                        "where the payment was processed in the wrong currency."
                    ),
                )
            )
            continue

        if voucher.amount == Decimal("0"):
            continue

        diff = abs(voucher.amount - payment.amount)
        pct = diff / abs(voucher.amount)

        if pct <= tolerance:
            continue

        if pct > high_threshold:
            severity = Severity.HIGH
        elif pct > medium_threshold:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        issues.append(
            ReconciliationIssue(
                transaction_id=voucher.transaction_id,
                issue_type=IssueType.AMOUNT_MISMATCH,
                severity=severity,
                detected_at=datetime.now(UTC).replace(tzinfo=None),
                description=(
                    f"Amount mismatch for transaction {voucher.transaction_id}: "
                    f"voucher={voucher.amount} {voucher.currency}, "
                    f"payment={payment.amount} {payment.currency} "
                    f"(difference: {pct * 100:.2f}%)"
                ),
                amount_at_risk=diff,
                payment_method=voucher.payment_method,
                currency=voucher.currency,
                suggested_resolution=(
                    "Auto-approve if under 1% tolerance threshold. "
                    "For larger discrepancies, escalate to finance team for manual review."
                    if severity == Severity.LOW
                    else "Escalate to finance team for manual review and reconciliation."
                ),
            )
        )
    return issues
