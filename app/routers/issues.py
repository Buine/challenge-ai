from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import IssueSummary, PaginatedIssues
from app.services.issues import get_summary, query_issues

router = APIRouter(tags=["issues"])


@router.get("/issues", response_model=PaginatedIssues)
def list_issues(
    issue_type: str | None = Query(None, description="Filter by issue type"),
    severity: str | None = Query(None, description="Filter by severity"),
    payment_method: str | None = Query(None, description="Filter by payment method"),
    currency: str | None = Query(None, description="Filter by currency"),
    date_from: str | None = Query(None, description="Filter issues detected after this date"),
    date_to: str | None = Query(None, description="Filter issues detected before this date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return query_issues(
        db,
        issue_type=issue_type,
        severity=severity,
        payment_method=payment_method,
        currency=currency,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/issues/summary", response_model=IssueSummary)
def issues_summary(db: Session = Depends(get_db)):
    return get_summary(db)
