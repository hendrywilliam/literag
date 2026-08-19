from fastapi import FastAPI

from app.api.routes import documents, query

app = FastAPI(title="literag", version="0.1.0")

app.include_router(documents.router)
app.include_router(query.router)

@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok"}
