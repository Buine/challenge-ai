import threading
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from app.database import SessionLocal
from app.services.detection import run_detection
from app.services.ingestion import ingest_payments, ingest_settlements, ingest_vouchers
from app.schemas import PaymentIn, SettlementIn, VoucherIn


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


_jobs: dict[str, dict] = {}


def submit_batch(
    vouchers: list[VoucherIn],
    payments: list[PaymentIn],
    settlements: list[SettlementIn],
) -> str:
    job_id = f"batch-{uuid.uuid4().hex[:12]}"
    _jobs[job_id] = {
        "status": JobStatus.QUEUED,
        "created_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
        "progress": 0,
        "total": len(vouchers) + len(payments) + len(settlements),
        "summary": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_process_batch,
        args=(job_id, vouchers, payments, settlements),
        daemon=True,
    )
    thread.start()
    return job_id


def _process_batch(
    job_id: str,
    vouchers: list[VoucherIn],
    payments: list[PaymentIn],
    settlements: list[SettlementIn],
):
    _jobs[job_id]["status"] = JobStatus.PROCESSING
    try:
        db = SessionLocal()
        try:
            v_result = ingest_vouchers(db, vouchers)
            _jobs[job_id]["progress"] = len(vouchers)

            p_result = ingest_payments(db, payments)
            _jobs[job_id]["progress"] += len(payments)

            s_result = ingest_settlements(db, settlements)
            _jobs[job_id]["progress"] += len(settlements)

            detection_result = run_detection(db)

            _jobs[job_id]["status"] = JobStatus.COMPLETED
            _jobs[job_id]["summary"] = {
                "ingestion": {
                    "vouchers": {"created": v_result.created, "duplicates": v_result.duplicates},
                    "payments": {"created": p_result.created, "duplicates": p_result.duplicates},
                    "settlements": {"created": s_result.created, "duplicates": s_result.duplicates},
                },
                "detection": {
                    "issues_found": detection_result.new_issues_found,
                    "issues_by_type": detection_result.issues_by_type,
                },
            }
        finally:
            db.close()
    except Exception as e:
        _jobs[job_id]["status"] = JobStatus.FAILED
        _jobs[job_id]["error"] = str(e)


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)
