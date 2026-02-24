from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DetectionRunResponse
from app.services.detection import run_detection

router = APIRouter(tags=["detection"])


@router.post("/detection/run", response_model=DetectionRunResponse)
def run_detection_endpoint(db: Session = Depends(get_db)):
    return run_detection(db)
