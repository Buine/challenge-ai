from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import PaymentStatus
from app.models import PaymentConfirmation, ReconciliationIssue, SettlementRecord, VoucherRecord
from app.rules.amount_mismatch import detect_amount_mismatch
from app.rules.orphaned import detect_orphaned_payments
from app.rules.post_expiration import detect_post_expiration_payments
from app.rules.stuck_pending import detect_stuck_pending
from app.rules.zombie import detect_zombie_completions
from app.schemas import DetectionRunResponse


def run_detection(db: Session) -> DetectionRunResponse:
    previous_count = db.execute(select(func.count(ReconciliationIssue.id))).scalar() or 0
    db.query(ReconciliationIssue).delete()

    payments = db.execute(select(PaymentConfirmation)).scalars().all()
    vouchers = db.execute(select(VoucherRecord)).scalars().all()
    settlements = db.execute(select(SettlementRecord)).scalars().all()

    voucher_ids = {v.transaction_id for v in vouchers}
    confirmed_ids = {p.transaction_id for p in payments if p.status == PaymentStatus.CONFIRMED}
    voucher_map = {v.transaction_id: v for v in vouchers}
    pairs = [
        (voucher_map[p.transaction_id], p)
        for p in payments
        if p.transaction_id in voucher_map
    ]

    now = datetime.now(UTC).replace(tzinfo=None)
    all_issues = []
    all_issues += detect_orphaned_payments(payments, voucher_ids)
    all_issues += detect_stuck_pending(vouchers, confirmed_ids, now)
    all_issues += detect_amount_mismatch(pairs)
    all_issues += detect_zombie_completions(settlements, confirmed_ids, voucher_map)
    all_issues += detect_post_expiration_payments(pairs)

    db.bulk_save_objects(all_issues)
    db.commit()

    issues_by_type: dict[str, int] = {}
    for issue in all_issues:
        issues_by_type[issue.issue_type] = issues_by_type.get(issue.issue_type, 0) + 1

    return DetectionRunResponse(
        previous_issues_cleared=previous_count,
        new_issues_found=len(all_issues),
        issues_by_type=issues_by_type,
    )
