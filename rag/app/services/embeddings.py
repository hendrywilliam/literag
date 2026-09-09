from langchain_voyageai import VoyageAIEmbeddings

from app.core.config import get_settings

_embeddings: VoyageAIEmbeddings | None = None

def get_embeddings() -> VoyageAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        settings = get_settings()
        _embeddings = VoyageAIEmbeddings(
            voyage_api_key=settings.voyage_api_key,
            model=settings.voyage_model,
        )
    return _embeddings
