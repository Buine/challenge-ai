from datetime import datetime

from app.config import settings
from app.enums import IssueType, PaymentStatus, Severity
from app.models import ReconciliationIssue, VoucherRecord


def detect_stuck_pending(
    vouchers: list[VoucherRecord],
    confirmed_ids: set[str],
    now: datetime,
) -> list[ReconciliationIssue]:
    issues = []
    threshold_hours = settings.stuck_pending_threshold_hours
    high_threshold_hours = settings.stuck_pending_high_threshold_hours

    for voucher in vouchers:
        if voucher.status != PaymentStatus.PENDING:
            continue
        if voucher.transaction_id in confirmed_ids:
            continue

        age_hours = (now - voucher.created_at).total_seconds() / 3600

        if age_hours <= threshold_hours:
            continue

        severity = Severity.HIGH if age_hours > high_threshold_hours else Severity.MEDIUM

        issues.append(
            ReconciliationIssue(
                transaction_id=voucher.transaction_id,
                issue_type=IssueType.STUCK_PENDING,
                severity=severity,
                detected_at=now,
                description=(
                    f"Voucher {voucher.transaction_id} has been in PENDING state for "
                    f"{age_hours:.1f} hours without payment confirmation"
                ),
                amount_at_risk=voucher.amount,
                payment_method=voucher.payment_method,
                currency=voucher.currency,
                suggested_resolution=(
                    "Send a payment reminder to the customer. If past expiration window, "
                    "consider marking as EXPIRED and notifying the customer."
                ),
            )
        )
    return issues
