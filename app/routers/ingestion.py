from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import IngestionResponse, PaymentIn, SettlementIn, VoucherIn
from app.services.ingestion import ingest_payments, ingest_settlements, ingest_vouchers

router = APIRouter(tags=["ingestion"])


@router.post("/ingest/vouchers", response_model=IngestionResponse, status_code=201)
def ingest_vouchers_endpoint(vouchers: list[VoucherIn], db: Session = Depends(get_db)):
    return ingest_vouchers(db, vouchers)


@router.post("/ingest/payments", response_model=IngestionResponse, status_code=201)
def ingest_payments_endpoint(payments: list[PaymentIn], db: Session = Depends(get_db)):
    return ingest_payments(db, payments)


@router.post("/ingest/settlements", response_model=IngestionResponse, status_code=201)
def ingest_settlements_endpoint(settlements: list[SettlementIn], db: Session = Depends(get_db)):
    return ingest_settlements(db, settlements)
