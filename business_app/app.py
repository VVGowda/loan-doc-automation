import streamlit as st
import re
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Loan Document Automation", layout="centered")
st.title("Loan Document Automation")
st.caption("Upload documents, get automatic extraction and validation.")

# --- Section 1: Create Application ---
st.header("1. Create a Loan Application")

with st.form("create_application_form"):
    first_name = st.text_input("First Name (letters only)")
    if first_name and not re.match(r"^[A-Za-z\s\-']*$", first_name):
        st.caption(":red[Numbers and special characters are not allowed here.]")

    last_name = st.text_input("Last Name (letters only)")
    if last_name and not re.match(r"^[A-Za-z\s\-']*$", last_name):
        st.caption(":red[Numbers and special characters are not allowed here.]")

    phone_number = st.text_input("Phone Number (US) - digits only")
    if phone_number and not re.fullmatch(r"[\d\s\-\(\)\+]*", phone_number):
        st.caption(":red[Only numbers are allowed here.]")

    stated_income = st.number_input("Annual Income ($)", min_value=0.0, step=1000.0, format="%.2f")
    loan_amount = st.number_input("Loan Amount Requested ($)", min_value=0.0, step=1000.0, format="%.2f")

    submitted = st.form_submit_button("Create Application")

    if submitted:
        missing = []

        if not first_name.strip() or len(first_name.strip()) > 50 or not re.match(r"^[A-Za-z\s\-']+$", first_name.strip()):
            missing.append("First Name (letters only, under 50 characters)")
        if not last_name.strip() or len(last_name.strip()) > 50 or not re.match(r"^[A-Za-z\s\-']+$", last_name.strip()):
            missing.append("Last Name (letters only, under 50 characters)")

        if not re.fullmatch(r"[\d\s\-\(\)\+]+", phone_number.strip()):
            missing.append("Phone Number (digits only, no letters)")
            phone_digits = ""
        else:
            phone_digits = re.sub(r"\D", "", phone_number)
            if phone_digits.startswith("1") and len(phone_digits) == 11:
                phone_digits = phone_digits[1:]
            if len(phone_digits) != 10:
                missing.append("Phone Number (must be a valid 10-digit US number)")

        if stated_income <= 0:
            missing.append("Annual Income")
        if loan_amount <= 0:
            missing.append("Loan Amount Requested")

        if missing:
            st.warning(f"Please fix: {', '.join(missing)}.")
        else:
            response = requests.post(
                f"{API_BASE}/applications/",
                json={
                    "first_name": first_name.strip(),
                    "last_name": last_name.strip(),
                    "phone_number": phone_digits,
                    "stated_income": stated_income,
                    "loan_amount": loan_amount,
                },
            )
            if response.status_code == 200:
                data = response.json()
                st.session_state["application_id"] = data["id"]
                st.success(f"Application created: {data.get('application_code', data['id'])}")
            else:
                try:
                    detail = response.json().get("detail", "Something went wrong.")
                except ValueError:
                    detail = f"Server error ({response.status_code}). Check the backend terminal for details."
                st.error(f"Error: {detail}")

st.divider()

# --- Section 2: Upload Document ---
st.header("2. Upload a Document")

if "application_id" not in st.session_state:
    st.info("Create an application above first.")
else:
    st.write(f"Uploading for Application ID: **{st.session_state['application_id']}**")

    document_type = st.selectbox("Document Type", ["pay_stub", "bank_statement"])
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    if st.button("Upload Document"):
        if uploaded_file is None:
            st.warning("Please select a file first.")
        else:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            params = {
                "document_type": document_type,
                "application_id": st.session_state["application_id"],
            }
            response = requests.post(f"{API_BASE}/documents/upload", params=params, files=files)

            if response.status_code == 200:
                data = response.json()
                st.success("Document uploaded and processed.")
                st.write("**Extracted Name:**", data.get("extracted_name") or "_Not found_")
                st.write("**Extracted Income:**", data.get("extracted_income") or "_Not found_")
                st.write("**Extracted Date:**", data.get("extracted_date") or "_Not found_")
            else:
                try:
                    detail = response.json().get("detail", "Something went wrong.")
                except ValueError:
                    detail = f"Server error ({response.status_code}). Check the backend terminal for details."
                st.error(f"Error: {detail}")

st.divider()

# --- Section 3: Validate ---
st.header("3. Run Validation")

if "application_id" in st.session_state:
    if st.button("Run Validation Check"):
        response = requests.post(f"{API_BASE}/applications/{st.session_state['application_id']}/validate")
        if response.status_code == 200:
            report = response.json()
            if report["is_valid"]:
                st.success("No critical issues found.")
            else:
                st.warning("Issues found - see below.")

            for flag in report["flags"]:
                if flag["severity"] == "error":
                    st.error(f"**{flag['field'].upper()}** — {flag['issue']}")
                else:
                    st.warning(f"**{flag['field'].upper()}** — {flag['issue']}")
        else:
            try:
                detail = response.json().get("detail", "Could not run validation.")
            except ValueError:
                detail = f"Server error ({response.status_code})."
            st.error(f"Error: {detail}")
else:
    st.info("Create an application and upload a document first.")