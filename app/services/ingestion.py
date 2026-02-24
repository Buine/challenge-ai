from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PaymentConfirmation, SettlementRecord, VoucherRecord
from app.schemas import IngestionResponse, PaymentIn, SettlementIn, VoucherIn


def ingest_vouchers(db: Session, vouchers: list[VoucherIn]) -> IngestionResponse:
    created = 0
    duplicates = 0
    for v in vouchers:
        existing = db.execute(
            select(VoucherRecord).where(VoucherRecord.transaction_id == v.transaction_id)
        ).scalar_one_or_none()
        if existing:
            duplicates += 1
            continue
        record = VoucherRecord(**v.model_dump())
        db.add(record)
        created += 1
    db.commit()
    return IngestionResponse(received=len(vouchers), created=created, duplicates=duplicates)


def ingest_payments(db: Session, payments: list[PaymentIn]) -> IngestionResponse:
    created = 0
    duplicates = 0
    for p in payments:
        existing = db.execute(
            select(PaymentConfirmation).where(
                PaymentConfirmation.transaction_id == p.transaction_id
            )
        ).scalar_one_or_none()
        if existing:
            duplicates += 1
            continue
        record = PaymentConfirmation(**p.model_dump())
        db.add(record)
        created += 1
    db.commit()
    return IngestionResponse(received=len(payments), created=created, duplicates=duplicates)


def ingest_settlements(db: Session, settlements: list[SettlementIn]) -> IngestionResponse:
    created = 0
    duplicates = 0
    for s in settlements:
        existing = db.execute(
            select(SettlementRecord).where(SettlementRecord.transaction_id == s.transaction_id)
        ).scalar_one_or_none()
        if existing:
            duplicates += 1
            continue
        record = SettlementRecord(**s.model_dump())
        db.add(record)
        created += 1
    db.commit()
    return IngestionResponse(received=len(settlements), created=created, duplicates=duplicates)
