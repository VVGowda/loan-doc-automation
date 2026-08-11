import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def check_documents_are_duplicate_content(new_text: str, existing_texts: list[str]) -> dict:
    """Uses AI to judge whether a new document is substantially the same as an existing one."""
    if not existing_texts:
        return {"is_duplicate": False, "reason": None}

    combined_existing = "\n---\n".join(t[:2000] for t in existing_texts)
    prompt = f"""Compare the NEW document text to the EXISTING document(s) text below.
Determine if the NEW document is substantially the same document as one of the existing
ones (same pay period/statement dates/figures, just re-uploaded or lightly altered), versus
genuinely being a different document (e.g. a different month's statement).

Return ONLY a JSON object: {{"is_duplicate": true or false, "reason": "short explanation"}}

NEW document text:
{new_text[:2000]}

EXISTING document(s) text:
{combined_existing}

Respond with ONLY the JSON object."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").replace("json", "", 1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"is_duplicate": False, "reason": None}