from fastapi import FastAPI

app = FastAPI(
    title="Loan Document Automation API",
    description="AI-agent-powered extraction and validation of loan documents",
    version="0.1.0",
)

@app.get("/health")
def health():
    return {"status": "ok"}