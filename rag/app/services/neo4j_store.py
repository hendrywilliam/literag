import re
from typing import Any

from langchain_core.documents import Document
from langchain_neo4j import Neo4jVector

from app.core.config import get_settings
from app.models.schemas import (
    Chunk,
    DocumentDetail,
    DocumentSummary,
    Entity,
    EntityRelation,
    Relation,
)
from app.services.embeddings import get_embeddings

NODE_LABEL = "Chunk"
TEXT_PROP = "text"
EMBEDDING_PROP = "embedding"
ENTITY_LABEL = "__Entity__"


def sanitize_label(label: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", label).strip("_")
    return cleaned or "Entity"


class DocumentNotFoundError(Exception):
    pass


class ChunkNotFoundError(Exception):
    pass


class Neo4jVectorStore:
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

        self._store.query(
            f"CREATE CONSTRAINT IF NOT EXISTS "
            f"FOR (e:`{ENTITY_LABEL}`) REQUIRE e.id IS UNIQUE;"
        )

        return self._store

    def add_documents(self, documents: list[Document], ids: list[str]) -> None:
        self._store_or_create().add_documents(documents, ids=ids)

    def list_documents(self) -> list[DocumentSummary]:
        result = self._store_or_create().query(
            f"""
            MATCH (n:{NODE_LABEL})
            WHERE n.document_id IS NOT NULL
            WITH n.document_id AS document_id, n.source AS source, count(n) AS chunk_count
            OPTIONAL MATCH (d:Document {{document_id: document_id}})
            RETURN document_id, source, chunk_count,
                   coalesce(d.status, 'indexed') AS status
            ORDER BY source
            """
        )
        return [
            DocumentSummary(
                document_id=row["document_id"],
                source=row["source"],
                chunk_count=row["chunk_count"],
                status=row["status"],
            )
            for row in result
        ]

    def get_document(self, document_id: str) -> DocumentDetail:
        result = self._store_or_create().query(
            f"""
            MATCH (n:{NODE_LABEL} {{document_id: $document_id}})
            WITH n.document_id AS document_id, n.source AS source, count(n) AS chunk_count
            OPTIONAL MATCH (d:Document {{document_id: document_id}})
            RETURN document_id, source, chunk_count,
                   coalesce(d.status, 'indexed') AS status
            """,
            params={"document_id": document_id},
        )
        if not result:
            raise DocumentNotFoundError(document_id)
        row = result[0]
        return DocumentDetail(
            document_id=row["document_id"],
            source=row["source"],
            chunk_count=row["chunk_count"],
            status=row["status"],
        )

    def list_chunks(self, document_id: str) -> list[Chunk]:
        result = self._store_or_create().query(
            f"""
            MATCH (n:{NODE_LABEL} {{document_id: $document_id}})
            RETURN n.chunk_id AS chunk_id, n.document_id AS document_id,
                   n.source AS source, n.{TEXT_PROP} AS text, n.chunk_index AS chunk_index
            ORDER BY n.chunk_index
            """,
            params={"document_id": document_id},
        )
        return [self._to_chunk(row) for row in result]

    def get_chunk(self, document_id: str, chunk_id: str) -> Chunk:
        result = self._store_or_create().query(
            f"""
            MATCH (n:{NODE_LABEL} {{document_id: $document_id, chunk_id: $chunk_id}})
            RETURN n.chunk_id AS chunk_id, n.document_id AS document_id,
                   n.source AS source, n.{TEXT_PROP} AS text, n.chunk_index AS chunk_index
            """,
            params={"document_id": document_id, "chunk_id": chunk_id},
        )
        if not result:
            raise ChunkNotFoundError(chunk_id)
        return self._to_chunk(result[0])

    def similarity_search_with_score(
        self, query: str, k: int, filter: dict | None = None
    ) -> list[tuple[Document, float]]:
        return self._store_or_create().similarity_search_with_score(
            query, k=k, filter=filter
        )

    @staticmethod
    def _to_chunk(row: Any) -> Chunk:
        return Chunk(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            source=row["source"],
            text=row["text"],
            chunk_index=row.get("chunk_index", 0),
        )

    def create_document(self, document_id: str, source: str) -> None:
        self._store_or_create().query(
            """
            MERGE (d:Document {document_id: $document_id})
            SET d.source = $source, d.status = 'indexed'
            """,
            params={"document_id": document_id, "source": source},
        )

    def set_document_status(self, document_id: str, status: str) -> None:
        self._store_or_create().query(
            """
            MERGE (d:Document {document_id: $document_id})
            SET d.status = $status
            """,
            params={"document_id": document_id, "status": status},
        )

    def list_chunk_relations(self, document_id: str) -> list[Relation]:
        result = self._store_or_create().query(
            f"""
            MATCH (a:{NODE_LABEL} {{document_id: $document_id}})
                  -[r:RELATED]->(b:{NODE_LABEL} {{document_id: $document_id}})
            RETURN a.chunk_id AS source_chunk_id, b.chunk_id AS target_chunk_id,
                   r.type AS relation_type, r.description AS description
            """,
            params={"document_id": document_id},
        )
        return [
            Relation(
                source_chunk_id=row["source_chunk_id"],
                target_chunk_id=row["target_chunk_id"],
                relation_type=row["relation_type"],
                description=row["description"] or "",
            )
            for row in result
        ]

    def add_chunk_relations(self, relations: list[Relation]) -> None:
        data = [r.model_dump() for r in relations]
        self._store_or_create().query(
            f"""
            UNWIND $data AS row
            MATCH (a:{NODE_LABEL} {{chunk_id: row.source_chunk_id}})
            MATCH (b:{NODE_LABEL} {{chunk_id: row.target_chunk_id}})
            MERGE (a)-[r:RELATED]->(b)
            SET r.type = row.relation_type, r.description = row.description
            """,
            params={"data": data},
        )

    def link_chunks_to_entities(self, chunk_entities: dict[str, list[str]]) -> None:
        data = [
            {"chunk_id": chunk_id, "entity_id": entity_id}
            for chunk_id, entity_ids in chunk_entities.items()
            for entity_id in entity_ids
        ]
        if not data:
            return
        self._store_or_create().query(
            f"""
            UNWIND $data AS row
            MATCH (c:{NODE_LABEL} {{chunk_id: row.chunk_id}})
            MATCH (e:`{ENTITY_LABEL}` {{id: row.entity_id}})
            MERGE (c)-[:MENTIONS]->(e)
            """,
            params={"data": data},
        )

    def add_entities(self, nodes: list[dict], relationships: list[dict]) -> None:
        if nodes:
            self._store_or_create().query(
                f"""
                UNWIND $data AS row
                MERGE (e:`{ENTITY_LABEL}` {{id: row.id}})
                SET e += row.properties
                WITH e, row
                CALL apoc.create.addLabels(e, [row.label]) YIELD node
                RETURN count(node)
                """,
                params={"data": nodes},
            )
        if relationships:
            self._store_or_create().query(
                """
                UNWIND $data AS row
                MATCH (s:`__Entity__` {id: row.source})
                MATCH (t:`__Entity__` {id: row.target})
                CALL apoc.merge.relationship(s, row.type, {}, row.properties, t)
                YIELD rel
                RETURN count(rel)
                """,
                params={"data": relationships},
            )

    def list_entities(self, document_id: str) -> list[Entity]:
        result = self._store_or_create().query(
            f"""
            MATCH (c:{NODE_LABEL} {{document_id: $document_id}})-[:MENTIONS]->(e)
            RETURN e.id AS id, labels(e) AS labels, e AS props
            """,
            params={"document_id": document_id},
        )
        seen: set[str] = set()
        entities: list[Entity] = []
        for row in result:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            node = dict(row["props"])
            labels = [l for l in row["labels"] if l != ENTITY_LABEL]
            node_type = labels[0] if labels else ENTITY_LABEL
            entities.append(
                Entity(
                    id=row["id"],
                    type=node_type,
                    properties={
                        k: v for k, v in node.items() if k not in {"id", "embedding"}
                    },
                )
            )
        return entities

    def list_entity_relations(self, document_id: str) -> list[EntityRelation]:
        result = self._store_or_create().query(
            f"""
            MATCH (c:{NODE_LABEL} {{document_id: $document_id}})-[:MENTIONS]->(e)
            WITH collect(distinct e) AS entities
            UNWIND entities AS e
            MATCH (e)-[r]->(t)
            WHERE t IN entities
            RETURN e.id AS source_id, labels(e) AS source_labels,
                   type(r) AS relation_type,
                   t.id AS target_id, labels(t) AS target_labels
            """,
            params={"document_id": document_id},
        )
        relations: list[EntityRelation] = []
        for row in result:
            source_labels = [l for l in row["source_labels"] if l != ENTITY_LABEL]
            target_labels = [l for l in row["target_labels"] if l != ENTITY_LABEL]
            relations.append(
                EntityRelation(
                    source_id=row["source_id"],
                    source_type=source_labels[0] if source_labels else ENTITY_LABEL,
                    relation_type=row["relation_type"],
                    target_id=row["target_id"],
                    target_type=target_labels[0] if target_labels else ENTITY_LABEL,
                )
            )
        return relations


_store: Neo4jVectorStore | None = None


def get_neo4j_vector_store() -> Neo4jVectorStore:
    global _store
    if _store is None:
        _store = Neo4jVectorStore()
    return _store
