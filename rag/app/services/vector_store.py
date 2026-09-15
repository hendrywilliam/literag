from langchain_core.documents import Document
from langchain_neo4j import Neo4jVector

from app.core.config import get_settings
from app.services.constants import EMBEDDING_PROP, NODE_LABEL, TEXT_PROP
from app.services.embeddings import get_embeddings


class VectorStore:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._embeddings = get_embeddings()
        self._store: Neo4jVector | None = None

    def _connection_kwargs(self) -> dict:
        return {
            "url": self._settings.neo4j_uri,
            "username": self._settings.neo4j_username,
            "password": self._settings.neo4j_password,
            "database": self._settings.neo4j_database,
        }

    def _store_or_create(self) -> Neo4jVector:
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

    def add_documents(self, documents: list[Document], ids: list[str]) -> None:
        self._store_or_create().add_documents(documents, ids=ids)

    def similarity_search_with_score(
        self, query: str, k: int, filter: dict | None = None
    ) -> list[tuple[Document, float]]:
        return self._store_or_create().similarity_search_with_score(
            query, k=k, filter=filter
        )


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
