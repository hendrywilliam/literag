import voyageai

from app.core.config import get_settings
from app.reranking.base import BaseReranker, RerankResult


class VoyageReranker(BaseReranker):
    """Re-rank documents using the Voyage AI rerank API."""

    def __init__(
        self, api_key: str | None = None, model: str | None = None
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.voyage_api_key
        self._model = model or settings.rerank_model
        self._client = voyageai.Client(api_key=self._api_key)

    def rerank(
        self, query: str, documents: list[str], top_k: int | None = None
    ) -> list[RerankResult]:
        response = self._client.rerank(
            query=query,
            documents=documents,
            model=self._model,
            top_k=top_k,
        )
        return [
            RerankResult(index=result.index, relevance_score=result.relevance_score)
            for result in response.results
        ]


_reranker: VoyageReranker | None = None


def get_voyage_reranker() -> VoyageReranker:
    global _reranker
    if _reranker is None:
        _reranker = VoyageReranker()
    return _reranker
