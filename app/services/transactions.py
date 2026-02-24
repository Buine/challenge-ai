from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PaymentConfirmation, ReconciliationIssue, SettlementRecord, VoucherRecord
from app.schemas import IssueResponse, SourceRecord, TransactionView


def _model_to_dict(obj) -> dict:
    return {
        c.name: (str(v) if hasattr(v, "isoformat") or isinstance(v, Decimal) else v)
        for c in obj.__table__.columns
        if (v := getattr(obj, c.name)) is not None and c.name not in ("id",)
    }


def get_transaction_view(db: Session, transaction_id: str) -> TransactionView | None:
    voucher = db.execute(
        select(VoucherRecord).where(VoucherRecord.transaction_id == transaction_id)
    ).scalar_one_or_none()

    payment = db.execute(
        select(PaymentConfirmation).where(
            PaymentConfirmation.transaction_id == transaction_id
        )
    ).scalar_one_or_none()

    settlement = db.execute(
        select(SettlementRecord).where(SettlementRecord.transaction_id == transaction_id)
    ).scalar_one_or_none()

    if not voucher and not payment and not settlement:
        return None

    issues_rows = db.execute(
        select(ReconciliationIssue).where(
            ReconciliationIssue.transaction_id == transaction_id
        )
    ).scalars().all()

    issues = [
        IssueResponse(
            id=i.id,
            transaction_id=i.transaction_id,
            issue_type=i.issue_type,
            severity=i.severity,
            detected_at=i.detected_at,
            description=i.description,
            amount_at_risk=i.amount_at_risk,
            payment_method=i.payment_method,
            currency=i.currency,
            suggested_resolution=i.suggested_resolution,
        )
        for i in issues_rows
    ]

    sources_present = sum(bool(x) for x in [voucher, payment, settlement])
    if payment and not voucher:
        status = "orphaned"
    elif sources_present == 3:
        status = "complete"
    else:
        status = "partial"

    return TransactionView(
        transaction_id=transaction_id,
        voucher=SourceRecord(source_system=voucher.source_system, data=_model_to_dict(voucher)) if voucher else None,
        payment=SourceRecord(source_system=payment.source_system, data=_model_to_dict(payment)) if payment else None,
        settlement=SourceRecord(source_system=settlement.source_system, data=_model_to_dict(settlement)) if settlement else None,
        issues=issues,
        status=status,
    )
