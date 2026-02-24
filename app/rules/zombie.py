from datetime import UTC, datetime

from app.enums import IssueType, PaymentStatus, Severity
from app.models import ReconciliationIssue, SettlementRecord, VoucherRecord


def detect_zombie_completions(
    settlements: list[SettlementRecord],
    confirmed_ids: set[str],
    voucher_map: dict[str, VoucherRecord] | None = None,
) -> list[ReconciliationIssue]:
    issues = []
    if voucher_map is None:
        voucher_map = {}
    for settlement in settlements:
        if settlement.status != PaymentStatus.COMPLETED:
            continue
        if settlement.transaction_id in confirmed_ids:
            continue
        voucher = voucher_map.get(settlement.transaction_id)
        payment_method = voucher.payment_method if voucher else None
        issues.append(
            ReconciliationIssue(
                transaction_id=settlement.transaction_id,
                issue_type=IssueType.ZOMBIE_COMPLETION,
                severity=Severity.HIGH,
                detected_at=datetime.now(UTC).replace(tzinfo=None),
                description=(
                    f"Transaction {settlement.transaction_id} was marked COMPLETED "
                    f"but never went through CONFIRMED state — "
                    f"no payment confirmation record exists"
                ),
                amount_at_risk=settlement.amount,
                payment_method=payment_method,
                currency=settlement.currency,
                suggested_resolution=(
                    "Verify if the payment was actually confirmed. "
                    "The settlement may have been processed without proper confirmation, "
                    "which could indicate a system bypass or data sync issue."
                ),
            )
        )
    return issues
