from datetime import UTC, datetime

from app.enums import IssueType, Severity
from app.models import PaymentConfirmation, ReconciliationIssue, VoucherRecord


def detect_post_expiration_payments(
    pairs: list[tuple[VoucherRecord, PaymentConfirmation]],
) -> list[ReconciliationIssue]:
    issues = []
    for voucher, payment in pairs:
        if voucher.expires_at is None:
            continue
        if payment.paid_at <= voucher.expires_at:
            continue
        issues.append(
            ReconciliationIssue(
                transaction_id=voucher.transaction_id,
                issue_type=IssueType.POST_EXPIRATION_PAYMENT,
                severity=Severity.HIGH,
                detected_at=datetime.now(UTC).replace(tzinfo=None),
                description=(
                    f"Payment for transaction {voucher.transaction_id} was received at "
                    f"{payment.paid_at.isoformat()} but the voucher expired at "
                    f"{voucher.expires_at.isoformat()}"
                ),
                amount_at_risk=payment.amount,
                payment_method=voucher.payment_method,
                currency=voucher.currency,
                suggested_resolution=(
                    "Process a refund to the customer since the voucher had expired. "
                    "Review store network for delayed payment transmissions."
                ),
            )
        )
    return issues
