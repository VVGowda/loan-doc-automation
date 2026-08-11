import pdfplumber
import re
from io import BytesIO


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts all raw text from a PDF file's bytes."""
    text = ""
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def find_income(text: str) -> float | None:
    """Looks for common income patterns like 'Gross Pay: $4,500.00'."""
    patterns = [
        r"gross\s*pay[:\s]+\$?([\d,]+\.\d{2})",
        r"net\s*pay[:\s]+\$?([\d,]+\.\d{2})",
        r"total\s*income[:\s]+\$?([\d,]+\.\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", "")
            return float(value)
    return None


def find_name(text: str) -> str | None:
    """Looks for a line like 'Employee Name: John Smith' or 'Name: John Smith'."""
    match = re.search(r"(?:employee\s*)?name[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().split("\n")[0]
    return None


def find_date(text: str) -> str | None:
    """Looks for a date pattern like MM/DD/YYYY."""
    match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", text)
    if match:
        return match.group(1)
    return None

def find_all_statement_periods(text: str) -> list[tuple[str, str]]:
    """Finds all 'MM/DD/YYYY - MM/DD/YYYY' style date ranges in the text, in the order they appear."""
    pattern = r"(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d{1,2}/\d{1,2}/\d{4})"
    return re.findall(pattern, text)

def find_pay_frequency(text: str) -> tuple[str, float] | None:
    """
    Detects pay frequency from 'Pay Begin Date' / 'Pay End Date' fields,
    and returns (frequency_label, periods_per_year) to annualize income.
    Returns None if no pay period could be determined (e.g. bank statements).
    """
    begin_match = re.search(r"pay\s*begin\s*date[:\s]+(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)
    end_match = re.search(r"pay\s*end\s*date[:\s]+(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)

    if not (begin_match and end_match):
        return None

    from datetime import datetime
    try:
        begin_date = datetime.strptime(begin_match.group(1), "%m/%d/%Y")
        end_date = datetime.strptime(end_match.group(1), "%m/%d/%Y")
    except ValueError:
        return None

    days = (end_date - begin_date).days + 1

    if 5 <= days <= 9:
        return ("weekly", 52)
    elif 12 <= days <= 16:
        return ("biweekly_or_semimonthly", 26)
    elif 27 <= days <= 32:
        return ("monthly", 12)
    else:
        return None