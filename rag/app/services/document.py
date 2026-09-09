import uuid

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.models.schemas import Chunk, DocumentDetail, DocumentSummary
from app.services.neo4j_store import get_neo4j_vector_store


class DocumentService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._store = get_neo4j_vector_store()

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

        self._store.create_document(document_id, filename)
        self._store.add_documents(chunks, ids=[c.metadata["chunk_id"] for c in chunks])

        return document_id, len(chunks)

    def list_documents(self) -> list[DocumentSummary]:
        return self._store.list_documents()

    def get_document(self, document_id: str) -> DocumentDetail:
        return self._store.get_document(document_id)

    def list_chunks(self, document_id: str) -> list[Chunk]:
        return self._store.list_chunks(document_id)

    def get_chunk(self, document_id: str, chunk_id: str) -> Chunk:
        return self._store.get_chunk(document_id, chunk_id)

    def list_chunk_relations(self, document_id: str):
        return self._store.list_chunk_relations(document_id)

    def list_entities(self, document_id: str):
        return self._store.list_entities(document_id)

    def list_entity_relations(self, document_id: str):
        return self._store.list_entity_relations(document_id)
