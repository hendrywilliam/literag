import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import documents, query
from app.db.neo4j import check_neo4j_connectivity, close_neo4j_driver


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        check_neo4j_connectivity()
    except Exception as exc:
        print(f"[fatal] {exc}", file=sys.stderr)
        sys.exit(1)
    yield
    close_neo4j_driver()


app = FastAPI(title="literag", version="0.1.0", lifespan=lifespan)

app.include_router(documents.router)
app.include_router(query.router)

@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok"}
