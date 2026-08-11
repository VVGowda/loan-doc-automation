import re
from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from datetime import datetime


class DocumentBase(BaseModel):
    """Fields common to a document when creating or reading it."""
    filename: str
    document_type: Literal["pay_stub", "bank_statement"]


class DocumentCreate(DocumentBase):
    """What we receive when a document is uploaded."""
    pass


class DocumentOut(DocumentBase):
    """What we return after processing a document."""
    id: int
    extracted_name: Optional[str] = None
    extracted_income: Optional[float] = None
    extracted_date: Optional[str] = None
    raw_text: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True  # lets Pydantic read data from SQLAlchemy objects


class LoanApplicationCreate(BaseModel):
    """What a loan officer/BA submits to start an application."""
    first_name: str
    last_name: str
    phone_number: str
    stated_income: float
    loan_amount: float

    @field_validator("first_name", "last_name")
    @classmethod
    def name_must_be_clean(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be empty.")
        if len(v) > 50:
            raise ValueError("This field must be 50 characters or fewer.")
        if not re.match(r"^[A-Za-z\s\-']+$", v):
            raise ValueError("Only letters are allowed - no numbers or special characters.")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_us_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if digits.startswith("1") and len(digits) == 11:
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError(
                "Please enter a valid 10-digit US phone number, e.g. 412-555-0100."
            )
        return digits

    @field_validator("stated_income", "loan_amount")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Value must be greater than zero.")
        if v > 100_000_000:
            raise ValueError("Value exceeds realistic limit.")
        return v


class LoanApplicationOut(LoanApplicationCreate):
    """What we return when reading back an application."""
    id: int
    application_code: str
    created_at: datetime

    class Config:
        from_attributes = True


class ValidationFlag(BaseModel):
    """A single issue found during validation."""
    field: str
    issue: str
    severity: str  # "warning" or "error"


class ValidationReport(BaseModel):
    """Full validation result for an application."""
    application_id: int
    is_valid: bool
    flags: list[ValidationFlag]