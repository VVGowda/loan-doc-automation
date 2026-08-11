import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def extract_fields_with_ai(raw_text: str) -> dict:
    """
    Sends raw PDF text to Claude and asks for structured fields back.
    Works on ANY document layout, not just specific formats.
    """
    prompt = f"""Extract the following fields from this financial document text.
Return ONLY a JSON object, no other text, no markdown formatting.

Fields to extract:
- name: the person's full name (not a label like "Employee Name")
- income: the most relevant income figure as a plain number (no $ or commas). Prefer gross pay, net pay, or total income — pick whichever is clearly the person's actual pay amount.
- date: the most relevant date on the document, in MM/DD/YYYY format
- document_type_guess: your best guess at what kind of document this is (e.g. "pay_stub", "bank_statement", "other")

If a field cannot be confidently found, use null for that field.

Document text:
{raw_text[:4000]}

Respond with ONLY the JSON object."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_response = response.content[0].text.strip()

    # Clean up in case the model wraps it in markdown fences
    if raw_response.startswith("```"):
        raw_response = raw_response.strip("`").replace("json", "", 1).strip()

    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        return {"name": None, "income": None, "date": None, "document_type_guess": None}