from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas import PaymentIn, SettlementIn, VoucherIn
from app.services.batch import get_job, submit_batch

router = APIRouter(tags=["batch"])


class BatchRequest(BaseModel):
    vouchers: list[VoucherIn] = []
    payments: list[PaymentIn] = []
    settlements: list[SettlementIn] = []


class BatchSubmitResponse(BaseModel):
    job_id: str
    status: str


@router.post("/batch/reconcile", response_model=BatchSubmitResponse)
def submit_batch_reconciliation(request: BatchRequest):
    job_id = submit_batch(request.vouchers, request.payments, request.settlements)
    return BatchSubmitResponse(job_id=job_id, status="queued")


@router.get("/batch/{job_id}")
def get_batch_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **job}
