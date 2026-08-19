from langchain_neo4j import Neo4jVector
from langchain_voyageai import VoyageAIEmbeddings

from app.core.config import get_settings

NODE_LABEL = "Chunk"
TEXT_PROP = "text"
EMBEDDING_PROP = "embedding"

class VectorStore:
    def __init__(self) -> None:
        settings = get_settings()
        self._embeddings = VoyageAIEmbeddings(
            voyage_api_key=settings.voyage_api_key,
            model=settings.voyage_model,
        )
        self._settings = settings
        self._store: Neo4jVector | None = None

    @property
    def embeddings(self) -> VoyageAIEmbeddings:
        return self._embeddings

    def _connection_kwargs(self) -> dict:
        return {
            "url": self._settings.neo4j_uri,
            "username": self._settings.neo4j_username,
            "password": self._settings.neo4j_password,
            "database": self._settings.neo4j_database,
        }

    def get_or_create(self) -> Neo4jVector:
        if self._store is not None:
            return self._store

        try:
            self._store = Neo4jVector.from_existing_index(
                self._embeddings,
                index_name=self._settings.neo4j_index_name,
                **self._connection_kwargs(),
            )
        except ValueError:
            self._store = Neo4jVector(
                self._embeddings,
                index_name=self._settings.neo4j_index_name,
                node_label=NODE_LABEL,
                embedding_node_property=EMBEDDING_PROP,
                text_node_property=TEXT_PROP,
                **self._connection_kwargs(),
            )
            self._store.create_new_index()
            self._store.query(
                f"CREATE CONSTRAINT IF NOT EXISTS "
                f"FOR (n:`{NODE_LABEL}`) REQUIRE n.id IS UNIQUE;"
            )

        return self._store


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
