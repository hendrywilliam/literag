import uuid
from typing import Any

from langchain_core.documents import Document
from langchain_neo4j import Neo4jVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.models.schemas import Chunk, DocumentDetail, DocumentSummary
from app.services.vector_store import NODE_LABEL, TEXT_PROP, get_vector_store


class DocumentNotFoundError(Exception):
    pass


class ChunkNotFoundError(Exception):
    pass


class DocumentService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._vector_store = get_vector_store()

    def _store(self) -> Neo4jVector:
        return self._vector_store.get_or_create()

    def _splitter(self) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter(
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )

    def upload_text(self, content: str, filename: str) -> tuple[str, int]:
        document_id = str(uuid.uuid4())
        document = Document(page_content=content, metadata={"source": filename})

        chunks = self._splitter().split_documents([document])
        for index, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = str(uuid.uuid4())
            chunk.metadata["document_id"] = document_id
            chunk.metadata["chunk_index"] = index

        self._store().add_documents(chunks, ids=[c.metadata["chunk_id"] for c in chunks])

        return document_id, len(chunks)

    def list_documents(self) -> list[DocumentSummary]:
        result = self._store().query(
            f"""
            MATCH (n:{NODE_LABEL})
            WHERE n.document_id IS NOT NULL
            RETURN n.document_id AS document_id, n.source AS source, count(n) AS chunk_count
            ORDER BY n.source
            """
        )
        return [
            DocumentSummary(
                document_id=row["document_id"],
                source=row["source"],
                chunk_count=row["chunk_count"],
            )
            for row in result
        ]

    def get_document(self, document_id: str) -> DocumentDetail:
        result = self._store().query(
            f"""
            MATCH (n:{NODE_LABEL} {{document_id: $document_id}})
            RETURN n.document_id AS document_id, n.source AS source, count(n) AS chunk_count
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
        )

    def list_chunks(self, document_id: str) -> list[Chunk]:
        result = self._store().query(
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
        result = self._store().query(
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

    @staticmethod
    def _to_chunk(row: Any) -> Chunk:
        return Chunk(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            source=row["source"],
            text=row["text"],
        )
