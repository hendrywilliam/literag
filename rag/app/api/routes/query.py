from fastapi import APIRouter

from app.models.schemas import QueryRequest, QueryResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    return RetrievalService().search(request.question, request.top_k)
