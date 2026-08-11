from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routers import documents, applications 




@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Loan Document Automation API",
    description="AI-agent-powered extraction and validation of loan documents",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(documents.router)
app.include_router(applications.router)


@app.get("/health")
def health():
    return {"status": "ok"}