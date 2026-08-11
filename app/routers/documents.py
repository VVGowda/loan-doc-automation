from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Literal
import hashlib

from app.database import get_db, Document, LoanApplication
from app.extraction.pdf_extractor import extract_text_from_pdf
from app.extraction.ai_extractor import extract_fields_with_ai
from app.extraction.similarity_checker import check_documents_are_duplicate_content
from app.models import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_DOCUMENTS_PER_APPLICATION = 3
MAX_FILE_SIZE_BYTES = {
    "pay_stub": 10 * 1024 * 1024,
    "bank_statement": 20 * 1024 * 1024,
}


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    document_type: Literal["pay_stub", "bank_statement"],
    application_id: int | None = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a pay stub or bank statement (PDF). Only regular-income documents are accepted.
    Rules enforced:
    - Only 'pay_stub' or 'bank_statement' allowed.
    - Max file size: 10MB (pay stub), 20MB (bank statement).
    - Application must exist.
    - Max 3 documents per application, no mixing types.
    - Exact duplicate files rejected.
    - AI-detected near-duplicate content rejected.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported right now.")

    file_bytes = await file.read()

    max_size = MAX_FILE_SIZE_BYTES[document_type]
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {max_size // (1024 * 1024)}MB limit for {document_type} documents.",
        )

    content_hash = hashlib.sha256(file_bytes).hexdigest()

    existing_docs = []
    if application_id is not None:
        application_exists = db.query(LoanApplication).filter(LoanApplication.id == application_id).first()
        if not application_exists:
            raise HTTPException(status_code=404, detail=f"Application {application_id} does not exist.")

        existing_docs = (
            db.query(Document).filter(Document.application_id == application_id).all()
        )

        if len(existing_docs) >= MAX_DOCUMENTS_PER_APPLICATION:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This application already has {len(existing_docs)} document(s). "
                    f"Maximum allowed is {MAX_DOCUMENTS_PER_APPLICATION}."
                ),
            )

        existing_types = {doc.document_type for doc in existing_docs}
        if existing_types and document_type not in existing_types:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This application already has '{list(existing_types)[0]}' documents uploaded. "
                    f"Mixing document types is not allowed — your loan application will be rejected "
                    f"if types are mixed. Please select one document type, or delete existing documents first."
                ),
            )

        for doc in existing_docs:
            if doc.content_hash == content_hash:
                raise HTTPException(
                    status_code=409,
                    detail=f"This exact file has already been uploaded as '{doc.filename}'.",
                )

    raw_text = extract_text_from_pdf(file_bytes)

    if existing_docs:
        existing_texts = [d.raw_text for d in existing_docs if d.raw_text]
        similarity = check_documents_are_duplicate_content(raw_text, existing_texts)
        if similarity.get("is_duplicate"):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Please check — these attachments seem to be the same document. "
                    f"({similarity.get('reason', 'Content appears to match an existing upload.')})"
                ),
            )

    ai_fields = extract_fields_with_ai(raw_text)
    extracted_name = ai_fields.get("name")
    extracted_income = ai_fields.get("income")
    extracted_date = ai_fields.get("date")

    db_document = Document(
        filename=file.filename,
        document_type=document_type,
        extracted_name=extracted_name,
        extracted_income=extracted_income,
        extracted_date=extracted_date,
        raw_text=raw_text,
        uploaded_at=datetime.utcnow(),
        application_id=application_id,
        content_hash=content_hash,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    db.delete(document)
    db.commit()
    return {"detail": f"Document {document_id} deleted."}