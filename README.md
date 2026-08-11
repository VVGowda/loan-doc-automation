# Loan Document Automation

AI-agent-powered extraction and validation of loan documents, built as a demonstration project for API-driven fintech and lending automation workflows.

This is a demo project, not a production system. It simulates a loan document automation pipeline - the kind of process a lending platform team might build - to show comfort working across the full stack involved: REST API design with Swagger/OpenAPI documentation, AI-powered document extraction, rule-based validation logic, and a business-facing UI.

It is not affiliated with any bank and does not use real financial data, real credit checks, or real PII. The goal is to demonstrate familiarity with the pattern of building this kind of system, and to reason clearly about where a real implementation would need to go further. See [Known Limitations](#known-limitations) below for exactly where that line is drawn.

---

## What it does

A loan officer or applicant:
1. Creates a loan application (name, phone, income, loan amount)
2. Uploads supporting documents (pay stubs or bank statements, as PDFs)
3. Gets automatic field extraction (name, income, date) via Claude
4. Runs validation, which cross-checks the application against the documents and flags anything a human reviewer would want to see

Two sides, by design:

- **Developer / API side** - a FastAPI backend with auto-generated Swagger docs at `/docs`, showing the full technical surface
- **Business-analyst side** - a plain-language Streamlit dashboard, so a non-technical user can run the whole workflow without touching JSON

---

## Architecture

**Envisioned production architecture** (what a real bank system would need):

```
Client app (OTP-verified login)
        |
API gateway (routing and orchestration)
        |
Document and identity checks (OCR, credit pull, employer check)
        |
Underwriting engine (DTI, fraud rules, risk score)
        |
Encrypted database (decision and notifications)
```

**What was actually built** (this repo):

```
Streamlit UI (business-analyst interface)
        |
FastAPI backend (REST API and Swagger docs)
        |
Claude AI extraction (name, income, date fields)
        |
Validation engine (ten rule-based checks)
        |
SQLite database (local file, no encryption)
```

Same shape, same stages - each stage here is a working simulation of what the real version would do.

---

## Features

**Document handling**
- Accepts only PDF pay stubs or bank statements
- Max 3 documents per application, no mixing types (pay stub + bank statement on the same application is rejected)
- File size limits: 10MB for pay stubs, 20MB for bank statements
- Exact duplicate file rejection (content hash comparison)
- AI-detected near-duplicate content rejection (e.g. the same statement re-uploaded with minor edits)

**AI-powered extraction**
- Uses Claude to pull applicant name, income, and document date from raw PDF text
- Works across varied document layouts - not hardcoded to one template
- Returns `null` rather than guessing when a field genuinely cannot be found

**Validation engine (10 checks)**
1. Missing income, name, or date extraction
2. Income mismatch vs. stated income, with pay-frequency detection (weekly/biweekly/monthly) and annualization before comparing
3. Applicant name mismatch between the application and any uploaded document
4. Cross-document name consistency (all documents must agree on who the applicant is)
5. Cross-document income consistency (flags >10% variance between pay periods)
6. Out-of-order statement periods within a single document (catches combined or shuffled documents)
7. Single-document staleness (a lone document should be recent - last month's pay stub, or last 6 months' bank statement)
8. Loan-amount sanity check (flags requests over 5x stated income)
9. Estimated debt-to-income ratio (flags above the common 43% qualified-loan threshold)
10. Input-level validation: names letters-only and capped at 50 characters, phone numbers validated as 10-digit US numbers, income/loan amounts must be positive and realistic

**Application safeguards**
- Duplicate-submission blocking (rejects an identical application resubmitted within 5 minutes)
- Auto-generated human-readable application codes (`APP-00001`, `APP-00002`, ...)
- Rejection of script-injection and SQL-injection-style patterns in text fields

---

## Screenshots

### API reference (Swagger)

| | |
|---|---|
| ![Swagger overview](screenshots/01-overview-swagger-and-editor.png) | Full API surface alongside the code editor, timestamp visible for provenance |
| ![Upload endpoint 1](screenshots/02-documents-upload-endpoint-1.png) | `POST /documents/upload` - rules and description |
| ![Upload endpoint 2](screenshots/02-documents-upload-endpoint-2.png) | Upload endpoint - parameters |
| ![Upload endpoint 3](screenshots/02-documents-upload-endpoint-3.png) | Upload endpoint - request body |
| ![Upload endpoint 4](screenshots/02-documents-upload-endpoint-4.png) | Upload endpoint - response schema |
| ![Upload endpoint 5](screenshots/02-documents-upload-endpoint-5.png) | Upload endpoint - validation error schema |
| ![Upload endpoint 6](screenshots/02-documents-upload-endpoint-6.png) | Upload endpoint - full detail continued |
| ![Upload endpoint 7](screenshots/02-documents-upload-endpoint-7.png) | Upload endpoint - full detail continued |

### The system in action (real requests, real data)

| | |
|---|---|
| ![Upload request](screenshots/08a-upload-request.png) | A real pay stub PDF submitted for upload |
| ![Extraction result](screenshots/08b-upload-response-extracted-data.png) | AI correctly extracts name and income from the raw document |
| ![Get document request](screenshots/09a-get-document-request.png) | Retrieving the same document by ID |
| ![Get document response](screenshots/09b-get-document-response.png) | Confirms the extracted data persisted correctly |
| ![Delete success](screenshots/10-delete-document-success.png) | Document deletion working as expected |
| ![Create application request](screenshots/11a-create-application-request.png) | A real loan application submitted |
| ![Create application response](screenshots/11b-create-application-response.png) | Application created with auto-generated code `APP-00001` |
| ![Get application](screenshots/12-get-application-response.png) | Application retrieved by ID, confirming storage |
| ![Validate request](screenshots/13a-validate-request.png) | Running validation on the application |
| ![Validate response](screenshots/13b-validate-response-flags.png) | **The core result**: income correctly annualized (biweekly detected, $40,122.68 vs. stated $58,000) and a stale-document warning (921 days old) |
| ![Health check](screenshots/14-health-check.png) | Basic uptime confirmation, executed live |
| ![Schemas overview](screenshots/15-schemas-overview.png) | All data models, executed live |

### Business-facing UI (Streamlit)

| | |
|---|---|
| ![Name and income mismatch](screenshots/16-streamlit-name-income-mismatch.png) | The business UI catching a real applicant-name mismatch and an annualized income mismatch, in plain language |
| ![Clean extraction success](screenshots/17-streamlit-clean-extraction-success.png) | A clean upload with correctly extracted name, income, and date |
| ![No issues found](screenshots/18-streamlit-no-issues-found.png) | A fully consistent application passing with zero flags - proves the system isn't flagging indiscriminately |
| ![Duplicate submission blocked](screenshots/19-streamlit-duplicate-submission-blocked.png) | Duplicate-submission protection rejecting a repeat application within the 5-minute window |

---

## Tech stack

| Layer | Tool |
|---|---|
| Backend / API | Python, FastAPI |
| API docs | Swagger UI (auto-generated via FastAPI/OpenAPI) |
| AI extraction | Anthropic Claude (Haiku) |
| PDF parsing | pdfplumber |
| Database | SQLite via SQLAlchemy |
| Business UI | Streamlit |
| Data validation | Pydantic |

---

## Setup and running locally

### Prerequisites

- Python 3.10+
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### 1. Clone and set up the environment

```powershell
git clone https://github.com/YOUR-USERNAME/loan-doc-automation.git
cd loan-doc-automation
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and add your real API key:

```
ANTHROPIC_API_KEY=your_actual_key_here
DATABASE_URL=sqlite:///./loans.db
```

`.env` is gitignored - your key never gets committed.

### 3. Run the backend (Terminal 1)

```powershell
venv\Scripts\activate
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

### 4. Run the business UI (Terminal 2, separate tab)

```powershell
venv\Scripts\activate
streamlit run business_app/app.py
```

- UI: `http://localhost:8501`

### Stopping

`Ctrl + C` in each terminal.

### Resetting the database

```powershell
Remove-Item loans.db
```

A fresh, empty database is created automatically the next time the backend starts.

---

## Known limitations

Named explicitly rather than glossed over, because knowing where the real gaps are matters more than pretending they don't exist.

- **No real authentication.** No login, no OTP. Phone number format is validated, but OTP verification was scoped as an architecture decision, not built - a real system would add SMS-based verification (e.g. via Twilio) right after the format check, before an application is created.
- **No credit bureau or employer verification integration.** What's called "fraud-adjacent" checking here is really consistency checking: duplicate file hashes, cross-document income variance, name mismatches, out-of-order statement periods. Real fraud and credit screening needs third-party services (Equifax/Experian/TransUnion, The Work Number) this project does not attempt to replicate.
- **No OCR fallback.** Scanned or image-only PDFs with no selectable text will not extract meaningfully. Only text-based PDFs are handled.
- **Simplified debt-to-income calculation.** Assumes a flat 5-year loan term and does not account for the applicant's existing debts - a rough proxy, not a real DTI calculation.
- **Net vs. gross income ambiguity.** Pay stub net pay is compared against stated gross annual income; these are legitimately different figures, and the system will flag a mismatch even when both numbers are "correct" in their own context.
- **Biweekly vs. semimonthly pay periods are not distinguished.** Both fall in a similar day-count window and are treated as biweekly (26 pay periods/year) for annualization purposes.
- **No encryption at rest.** Data lives in a plain SQLite file. No PII like SSN is collected by design, but even the data that is stored (name, phone, income) is unencrypted - a production system needs encryption, access controls, and audit logging.
- **Synthetic test data only.** All sample documents used during development were fictional, generated for testing. Real-world document diversity (scan quality, layout variety, edge cases) will exceed what this project was tested against.

---

## Why this project exists

This was built to demonstrate comfort operating in the kind of environment a loan enablement or fintech platform team works in - REST APIs with OpenAPI/Swagger documentation, AI-assisted document processing, validation logic, and the tradeoffs that come with each. It is not a claim to have built bank-grade infrastructure. It is a demonstration that the builder can reason clearly about where a real implementation would need to go further, having lived through the actual limitations while building this one.

---

## License

MIT - Copyright (c) 2026 VVG. See [LICENSE](LICENSE) for the full text.