from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()  # reads variables from .env

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./loans.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    document_type = Column(String, nullable=False)
    extracted_name = Column(String, nullable=True)
    extracted_income = Column(Float, nullable=True)
    extracted_date = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=True)
    content_hash = Column(String, nullable=True)


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_code = Column(String, unique=True, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    stated_income = Column(Float, nullable=False)
    loan_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Creates all tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Provides a database session, used as a FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()