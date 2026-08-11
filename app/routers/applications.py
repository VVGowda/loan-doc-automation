from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db, LoanApplication, Document
from app.models import LoanApplicationCreate, LoanApplicationOut, ValidationReport
from app.agents.validation_agent import validate_application

router = APIRouter(prefix="/applications", tags=["applications"])

DUPLICATE_WINDOW_MINUTES = 5


@router.post("/", response_model=LoanApplicationOut)
def create_application(application: LoanApplicationCreate, db: Session = Depends(get_db)):
    """Create a new loan application, blocking duplicate submissions via the database."""
    cutoff = datetime.utcnow() - timedelta(minutes=DUPLICATE_WINDOW_MINUTES)
    existing = (
        db.query(LoanApplication)
        .filter(
            LoanApplication.first_name == application.first_name,
            LoanApplication.last_name == application.last_name,
            LoanApplication.phone_number == application.phone_number,
            LoanApplication.loan_amount == application.loan_amount,
            LoanApplication.created_at >= cutoff,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A matching application ({existing.application_code}) was already submitted "
                f"in the last {DUPLICATE_WINDOW_MINUTES} minutes. Please wait, or check that application."
            ),
        )

    db_application = LoanApplication(
        first_name=application.first_name,
        last_name=application.last_name,
        phone_number=application.phone_number,
        stated_income=application.stated_income,
        loan_amount=application.loan_amount,
        created_at=datetime.utcnow(),
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)

    db_application.application_code = f"APP-{db_application.id:05d}"
    db.commit()
    db.refresh(db_application)

    return db_application


@router.get("/{application_id}", response_model=LoanApplicationOut)
def get_application(application_id: int, db: Session = Depends(get_db)):
    application = db.query(LoanApplication).filter(LoanApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    return application


@router.post("/{application_id}/validate", response_model=ValidationReport)
def validate(application_id: int, db: Session = Depends(get_db)):
    application = db.query(LoanApplication).filter(LoanApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    documents = db.query(Document).filter(Document.application_id == application_id).all()
    flags = validate_application(application, documents)

    return ValidationReport(
        application_id=application_id,
        is_valid=not any(f.severity == "error" for f in flags),
        flags=flags,
    )