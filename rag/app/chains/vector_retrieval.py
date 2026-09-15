from langchain_core.documents import Document

from app.chains.base import Chain
from app.core.config import get_settings
from app.models.schemas import QuerySource
from app.reranking import BaseReranker, get_voyage_reranker
from app.services.vector_store import VectorStore, get_vector_store


class VectorRetrieval(Chain[str, list[QuerySource]]):
    """Retrieve relevant chunks via vector search, optionally reranked."""

    def __init__(
        self,
        store: VectorStore | None = None,
        reranker: BaseReranker | None = None,
    ) -> None:
        self._settings = get_settings()
        self._store = store or get_vector_store()
        self._reranker = reranker

    def _get_reranker(self) -> BaseReranker:
        return self._reranker or get_voyage_reranker()

    def run(self, input: str, *, top_k: int | None = None) -> list[QuerySource]:
        k = top_k or self._settings.default_top_k

        if not self._settings.rerank_enabled:
            return self._search(input, k)

        fetch_k = max(k, self._settings.rerank_fetch_k)
        candidates = self._store.similarity_search_with_score(input, k=fetch_k)
        if not candidates:
            return []

        documents = [doc for doc, _ in candidates]
        reranked = self._get_reranker().rerank(
            input, [doc.page_content for doc in documents], top_k=k
        )

        return [
            self._to_source(documents[result.index], result.relevance_score)
            for result in reranked
        ]

    def _search(self, query: str, k: int) -> list[QuerySource]:
        results = self._store.similarity_search_with_score(query, k=k)
        return [
            self._to_source(doc, score)
            for doc, score in results
            if score >= self._settings.min_score
        ]

    @staticmethod
    def _to_source(doc: Document, score: float) -> QuerySource:
        return QuerySource(
            chunk_id=doc.metadata.get("chunk_id", ""),
            document_id=doc.metadata.get("document_id", ""),
            source=doc.metadata.get("source", ""),
            score=score,
            text=doc.page_content,
        )


_vector_retrieval: VectorRetrieval | None = None


def get_vector_retrieval() -> VectorRetrieval:
    global _vector_retrieval
    if _vector_retrieval is None:
        _vector_retrieval = VectorRetrieval()
    return _vector_retrieval
