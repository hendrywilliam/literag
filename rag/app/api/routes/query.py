from fastapi import APIRouter

from app.chains.vector_retrieval import get_vector_retrieval
from app.models.schemas import QueryRequest, QueryResponse

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    sources = get_vector_retrieval().run(request.question, top_k=request.top_k)
    return QueryResponse(question=request.question, sources=sources)
