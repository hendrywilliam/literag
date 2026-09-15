from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RerankResult:
    """A single reranked document with its relevance score."""

    index: int
    relevance_score: float


class BaseReranker(ABC):
    """Abstract base for rerankers.

    A reranker re-orders a list of candidate documents by how relevant they are
    to a query (using a model that scores query-document pairs, rather than
    plain vector similarity).
    """

    @abstractmethod
    def rerank(
        self, query: str, documents: list[str], top_k: int | None = None
    ) -> list[RerankResult]:
        """Re-rank documents against a query, best-first."""
        raise NotImplementedError
