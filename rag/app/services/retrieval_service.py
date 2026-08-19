from app.core.config import get_settings
from app.models.schemas import QueryResponse, QuerySource
from app.services.vector_store import get_vector_store


class RetrievalService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._vector_store = get_vector_store()

    def search(self, question: str, top_k: int | None = None) -> QueryResponse:
        k = top_k or self._settings.default_top_k
        store = self._vector_store.get_or_create()
        results = store.similarity_search_with_score(question, k=k)

        sources = [
            QuerySource(
                chunk_id=doc.metadata.get("chunk_id", ""),
                document_id=doc.metadata.get("document_id", ""),
                source=doc.metadata.get("source", ""),
                score=score,
                text=doc.page_content,
            )
            for doc, score in results
        ]

        return QueryResponse(question=question, sources=sources)
