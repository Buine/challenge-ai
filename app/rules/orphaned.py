from datetime import UTC, datetime

from app.enums import IssueType, Severity
from app.models import PaymentConfirmation, ReconciliationIssue


def detect_orphaned_payments(
    payments: list[PaymentConfirmation],
    voucher_ids: set[str],
) -> list[ReconciliationIssue]:
    issues = []
    for payment in payments:
        if payment.transaction_id not in voucher_ids:
            issues.append(
                ReconciliationIssue(
                    transaction_id=payment.transaction_id,
                    issue_type=IssueType.ORPHANED_PAYMENT,
                    severity=Severity.HIGH,
                    detected_at=datetime.now(UTC).replace(tzinfo=None),
                    description=(
                        f"Payment confirmation exists for transaction {payment.transaction_id} "
                        f"but no voucher record was found in the voucher system"
                    ),
                    amount_at_risk=payment.amount,
                    payment_method=payment.payment_method,
                    currency=payment.currency,
                    suggested_resolution=(
                        "Investigate if the voucher was generated in a different system or if "
                        "this is a fraudulent payment. Cross-reference with store POS records."
                    ),
                )
            )
    return issues
