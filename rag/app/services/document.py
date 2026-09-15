import uuid

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.models.schemas import Chunk, DocumentDetail, DocumentSummary
from app.services.graph_store import get_graph_store
from app.services.vector_store import get_vector_store


class DocumentService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._vector_store = get_vector_store()
        self._graph_store = get_graph_store()

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

        self._graph_store.create_document(document_id, filename)
        self._vector_store.add_documents(chunks, ids=[c.metadata["chunk_id"] for c in chunks])

        return document_id, len(chunks)

    def list_documents(self) -> list[DocumentSummary]:
        return self._graph_store.list_documents()

    def get_document(self, document_id: str) -> DocumentDetail:
        return self._graph_store.get_document(document_id)

    def list_chunks(self, document_id: str) -> list[Chunk]:
        return self._graph_store.list_chunks(document_id)

    def get_chunk(self, document_id: str, chunk_id: str) -> Chunk:
        return self._graph_store.get_chunk(document_id, chunk_id)

    def list_chunk_relations(self, document_id: str):
        return self._graph_store.list_chunk_relations(document_id)

    def list_entities(self, document_id: str):
        return self._graph_store.list_entities(document_id)

    def list_entity_relations(self, document_id: str):
        return self._graph_store.list_entity_relations(document_id)
