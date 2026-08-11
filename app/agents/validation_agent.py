from app.extraction.pdf_extractor import find_all_statement_periods, find_pay_frequency
from app.database import Document, LoanApplication
from app.models import ValidationFlag
from datetime import datetime
from statistics import mean


def validate_application(application: LoanApplication, documents: list[Document]) -> list[ValidationFlag]:
    """
    Runs a set of rule-based checks comparing the loan application
    against its linked documents, and returns a list of flags.
    """
    flags: list[ValidationFlag] = []

    if not documents:
        flags.append(ValidationFlag(
            field="documents",
            issue="No documents have been uploaded for this application.",
            severity="error",
        ))
        return flags

    for doc in documents:
        # Check 1: missing income
        if doc.extracted_income is None:
            flags.append(ValidationFlag(
                field="income",
                issue=f"Could not extract income from '{doc.filename}'. Manual review needed.",
                severity="warning",
            ))
        else:
            # Check 2: income mismatch vs stated income, annualizing if pay frequency is known
            comparison_income = doc.extracted_income
            frequency_note = ""

            if doc.document_type == "pay_stub" and doc.raw_text:
                frequency = find_pay_frequency(doc.raw_text)
                if frequency:
                    label, periods_per_year = frequency
                    comparison_income = doc.extracted_income * periods_per_year
                    frequency_note = (
                        f" (detected as {label.replace('_', ' ')} pay, annualized from "
                        f"{doc.extracted_income:,.2f} USD per period)"
                    )

            difference = abs(comparison_income - application.stated_income)
            tolerance = application.stated_income * 0.15  # allow 15% variance
            if difference > tolerance:
                flags.append(ValidationFlag(
                    field="income",
                    issue=(
                        f"Stated income ({application.stated_income:,.2f} USD) differs significantly "
                        f"from document '{doc.filename}' ({comparison_income:,.2f} USD annualized"
                        f"{frequency_note})."
                    ),
                    severity="error",
                ))

        # Check 3: missing name
        if doc.extracted_name is None:
            flags.append(ValidationFlag(
                field="name",
                issue=f"Could not extract applicant name from '{doc.filename}'. Manual review needed.",
                severity="warning",
            ))

        # Check 4: missing date
        if doc.extracted_date is None:
            flags.append(ValidationFlag(
                field="date",
                issue=f"Could not extract a document date from '{doc.filename}'.",
                severity="warning",
            ))

        else:
            # Check 3b: extracted document name must match the applicant's own name
            applicant_full_name = f"{application.first_name} {application.last_name}".strip().lower()
            doc_name_lower = doc.extracted_name.strip().lower()

            applicant_parts = set(applicant_full_name.split())
            doc_parts = set(doc_name_lower.split())

            if not (applicant_parts & doc_parts):
                flags.append(ValidationFlag(
                    field="name",
                    issue=(
                        f"Document '{doc.filename}' shows applicant name '{doc.extracted_name}', "
                        f"which does not match the application name "
                        f"'{application.first_name} {application.last_name}'."
                    ),
                    severity="error",
                ))

    # Check 5: loan amount sanity check
    if application.loan_amount > application.stated_income * 5:
        flags.append(ValidationFlag(
            field="loan_amount",
            issue=(
                f"Requested loan amount ({application.loan_amount:,.2f} USD) is more than 5x "
                f"stated annual income ({application.stated_income:,.2f} USD)."
            ),
            severity="warning",
        ))

    # Check 6: if only one document was uploaded, it must be recent
    if len(documents) == 1:
        doc = documents[0]
        if doc.extracted_date:
            try:
                doc_date = datetime.strptime(doc.extracted_date, "%m/%d/%Y")
                days_old = (datetime.utcnow() - doc_date).days
                max_age = 45 if doc.document_type == "pay_stub" else 190
                if days_old > max_age:
                    flags.append(ValidationFlag(
                        field="date",
                        issue=(
                            f"Only one document was provided and it is {days_old} days old. "
                            f"A single document should be the most recent available "
                            f"(e.g. last month's pay stub or last 6 months' bank statement)."
                        ),
                        severity="warning",
                    ))
            except ValueError:
                pass

    # Check 7: statement periods within each document must be chronological
    for doc in documents:
        if doc.raw_text:
            periods = find_all_statement_periods(doc.raw_text)
            if len(periods) > 1:
                try:
                    start_dates = [datetime.strptime(p[0], "%m/%d/%Y") for p in periods]
                    if start_dates != sorted(start_dates):
                        flags.append(ValidationFlag(
                            field="document_order",
                            issue=(
                                f"'{doc.filename}' contains multiple statement periods that are "
                                f"not in chronological order. Please check - attachments seem to be "
                                f"combined incorrectly or out of sequence."
                            ),
                            severity="error",
                        ))
                except ValueError:
                    pass

    # Check 8: income consistency across multiple documents (allow ~10% variance)
    incomes = [doc.extracted_income for doc in documents if doc.extracted_income is not None]
    if len(incomes) > 1:
        avg_income = mean(incomes)
        for doc in documents:
            if doc.extracted_income is not None and avg_income > 0:
                variance = abs(doc.extracted_income - avg_income) / avg_income
                if variance > 0.10:
                    flags.append(ValidationFlag(
                        field="income_consistency",
                        issue=(
                            f"'{doc.filename}' income ({doc.extracted_income:,.2f} USD) varies "
                            f"{variance:.0%} from the average across documents ({avg_income:,.2f} USD). "
                            f"More than 10% variance between pay periods may need manual review."
                        ),
                        severity="warning" if variance <= 0.25 else "error",
                    ))

    # Check 9: applicant name consistency across documents
    extracted_names = [doc.extracted_name for doc in documents if doc.extracted_name]
    if len(extracted_names) > 1:
        unique_names = set(n.strip().lower() for n in extracted_names)
        if len(unique_names) > 1:
            flags.append(ValidationFlag(
                field="name_consistency",
                issue=(
                    f"Documents show different applicant names: {', '.join(extracted_names)}. "
                    f"All documents must belong to the same applicant."
                ),
                severity="error",
            ))

    # Check 10: Debt-to-Income ratio (simplified estimate)
    if application.stated_income > 0:
        monthly_income = application.stated_income / 12
        monthly_loan_payment_estimate = application.loan_amount / 60  # rough 5-year term
        dti_ratio = monthly_loan_payment_estimate / monthly_income
        if dti_ratio > 0.43:
            flags.append(ValidationFlag(
                field="debt_to_income",
                issue=(
                    f"Estimated debt-to-income ratio is {dti_ratio:.0%}, above the common 43% "
                    f"threshold lenders use for qualified loans. This assumes a 5-year repayment "
                    f"term and does not include the applicant's existing debts."
                ),
                severity="warning",
            ))

    return flags