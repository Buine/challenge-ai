from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import TransactionView
from app.services.transactions import get_transaction_view

router = APIRouter(tags=["transactions"])


@router.get("/transactions/{transaction_id}", response_model=TransactionView)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    view = get_transaction_view(db, transaction_id)
    if not view:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return view
