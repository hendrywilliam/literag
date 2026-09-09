from app.core.config import get_settings
from app.models.schemas import QueryResponse, QuerySource
from app.services.neo4j_store import get_neo4j_vector_store


class RetrievalService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._store = get_neo4j_vector_store()

    def search(self, question: str, top_k: int | None = None) -> QueryResponse:
        k = top_k or self._settings.default_top_k
        results = self._store.similarity_search_with_score(question, k=k)

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
