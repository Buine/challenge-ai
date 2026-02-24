from decimal import Decimal

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models import (
    PaymentConfirmation,
    ReconciliationIssue,
    SettlementRecord,
    VoucherRecord,
)
from app.schemas import IssueResponse, IssueSummary, PaginatedIssues


def query_issues(
    db: Session,
    issue_type: str | None = None,
    severity: str | None = None,
    payment_method: str | None = None,
    currency: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedIssues:
    query = select(ReconciliationIssue)
    count_query = select(func.count(ReconciliationIssue.id))

    if issue_type:
        query = query.where(ReconciliationIssue.issue_type == issue_type)
        count_query = count_query.where(ReconciliationIssue.issue_type == issue_type)
    if severity:
        query = query.where(ReconciliationIssue.severity == severity)
        count_query = count_query.where(ReconciliationIssue.severity == severity)
    if payment_method:
        query = query.where(ReconciliationIssue.payment_method == payment_method)
        count_query = count_query.where(ReconciliationIssue.payment_method == payment_method)
    if currency:
        query = query.where(ReconciliationIssue.currency == currency)
        count_query = count_query.where(ReconciliationIssue.currency == currency)
    if date_from:
        query = query.where(ReconciliationIssue.detected_at >= date_from)
        count_query = count_query.where(ReconciliationIssue.detected_at >= date_from)
    if date_to:
        query = query.where(ReconciliationIssue.detected_at <= date_to)
        count_query = count_query.where(ReconciliationIssue.detected_at <= date_to)

    total = db.execute(count_query).scalar()
    rows = db.execute(
        query.order_by(ReconciliationIssue.detected_at.desc()).offset(offset).limit(limit)
    ).scalars().all()

    items = [
        IssueResponse(
            id=r.id,
            transaction_id=r.transaction_id,
            issue_type=r.issue_type,
            severity=r.severity,
            detected_at=r.detected_at,
            description=r.description,
            amount_at_risk=r.amount_at_risk,
            payment_method=r.payment_method,
            currency=r.currency,
            suggested_resolution=r.suggested_resolution,
        )
        for r in rows
    ]

    return PaginatedIssues(items=items, total=total, limit=limit, offset=offset)


def get_summary(db: Session) -> IssueSummary:
    total_issues = db.execute(select(func.count(ReconciliationIssue.id))).scalar() or 0

    type_counts = {}
    rows = db.execute(
        select(ReconciliationIssue.issue_type, func.count(ReconciliationIssue.id))
        .group_by(ReconciliationIssue.issue_type)
    ).all()
    for issue_type, count in rows:
        type_counts[issue_type] = count

    severity_counts = {}
    sev_rows = db.execute(
        select(ReconciliationIssue.severity, func.count(ReconciliationIssue.id))
        .group_by(ReconciliationIssue.severity)
    ).all()
    for severity, count in sev_rows:
        severity_counts[severity] = count

    total_at_risk = db.execute(
        select(func.coalesce(func.sum(ReconciliationIssue.amount_at_risk), 0))
    ).scalar()

    voucher_count = db.execute(select(func.count(VoucherRecord.id))).scalar() or 0
    payment_count = db.execute(select(func.count(PaymentConfirmation.id))).scalar() or 0
    settlement_count = db.execute(select(func.count(SettlementRecord.id))).scalar() or 0

    all_txn_ids = set()
    for model in [VoucherRecord, PaymentConfirmation, SettlementRecord]:
        ids = db.execute(select(model.transaction_id)).scalars().all()
        all_txn_ids.update(ids)
    total_transactions = len(all_txn_ids)

    txn_with_issues = db.execute(
        select(func.count(distinct(ReconciliationIssue.transaction_id)))
    ).scalar() or 0

    issue_rate = (
        Decimal(str(txn_with_issues)) / Decimal(str(total_transactions)) * 100
        if total_transactions > 0
        else Decimal("0")
    )

    return IssueSummary(
        total_issues=total_issues,
        issues_by_type=type_counts,
        issues_by_severity=severity_counts,
        total_amount_at_risk=total_at_risk,
        total_transactions=total_transactions,
        transactions_with_issues=txn_with_issues,
        issue_rate_percent=round(issue_rate, 2),
    )
