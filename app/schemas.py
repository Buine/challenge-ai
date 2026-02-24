from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class VoucherIn(BaseModel):
    transaction_id: str
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    source_system: str = "voucher_system"
    created_at: datetime
    expires_at: datetime | None = None
    customer_name: str | None = None
    store_id: str | None = None


class PaymentIn(BaseModel):
    transaction_id: str
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    source_system: str = "payment_processor"
    paid_at: datetime
    store_id: str | None = None


class SettlementIn(BaseModel):
    transaction_id: str
    amount: Decimal
    currency: str
    status: str
    source_system: str = "bank_settlement"
    settled_at: datetime


class IngestionResponse(BaseModel):
    received: int
    created: int
    duplicates: int


class SourceRecord(BaseModel):
    source_system: str
    data: dict


class IssueResponse(BaseModel):
    id: int
    transaction_id: str
    issue_type: str
    severity: str
    detected_at: datetime
    description: str
    amount_at_risk: Decimal
    payment_method: str | None
    currency: str | None
    suggested_resolution: str | None = None


class TransactionView(BaseModel):
    transaction_id: str
    voucher: SourceRecord | None = None
    payment: SourceRecord | None = None
    settlement: SourceRecord | None = None
    issues: list[IssueResponse] = []
    status: str


class DetectionRunResponse(BaseModel):
    previous_issues_cleared: int
    new_issues_found: int
    issues_by_type: dict[str, int]


class IssueSummary(BaseModel):
    total_issues: int
    issues_by_type: dict[str, int]
    issues_by_severity: dict[str, int]
    total_amount_at_risk: Decimal
    total_transactions: int
    transactions_with_issues: int
    issue_rate_percent: Decimal


class PaginatedIssues(BaseModel):
    items: list[IssueResponse]
    total: int
    limit: int
    offset: int
