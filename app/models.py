from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VoucherRecord(Base):
    __tablename__ = "voucher_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    payment_method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    source_system: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    store_id: Mapped[str | None] = mapped_column(String(50), nullable=True)


class PaymentConfirmation(Base):
    __tablename__ = "payment_confirmations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    payment_method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    source_system: Mapped[str] = mapped_column(String(50))
    paid_at: Mapped[datetime] = mapped_column(DateTime)
    store_id: Mapped[str | None] = mapped_column(String(50), nullable=True)


class SettlementRecord(Base):
    __tablename__ = "settlement_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(20))
    source_system: Mapped[str] = mapped_column(String(50))
    settled_at: Mapped[datetime] = mapped_column(DateTime)


class ReconciliationIssue(Base):
    __tablename__ = "reconciliation_issues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), index=True)
    issue_type: Mapped[str] = mapped_column(String(30), index=True)
    severity: Mapped[str] = mapped_column(String(10), index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    description: Mapped[str] = mapped_column(Text)
    amount_at_risk: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    payment_method: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_issues_type_severity", "issue_type", "severity"),
    )
