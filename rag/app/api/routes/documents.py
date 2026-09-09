import hashlib
from hashlib import sha256
import secrets
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.models.schemas import (
    Chunk,
    DocumentDetail,
    DocumentSummary,
    Entity,
    EntityRelation,
    Relation,
    RelationsBuildResponse,
    UploadResponse,
)
from app.services.document import DocumentService
from app.services.neo4j_store import (
    ChunkNotFoundError,
    DocumentNotFoundError,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")

    content = (await file.read()).decode("utf-8")
    if not content.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    rand = secrets.token_bytes(16)
    hash = hashlib.sha256(rand)
    fileName = hash.hexdigest()

    service = DocumentService()
    document_id, chunk_count = service.upload_text(content, fileName)

    if get_settings().relation_enabled:
        from app.tasks.relations import build_document_relations

        build_document_relations.delay(document_id)

    return UploadResponse(
        document_id=document_id,
        filename=fileName,
        chunk_count=chunk_count,
    )


@router.get("", response_model=list[DocumentSummary])
async def list_documents() -> list[DocumentSummary]:
    return DocumentService().list_documents()


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: str) -> DocumentDetail:
    try:
        return DocumentService().get_document(document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("/{document_id}/chunks", response_model=list[Chunk])
async def list_chunks(document_id: str) -> list[Chunk]:
    try:
        return DocumentService().list_chunks(document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("/{document_id}/chunks/{chunk_id}", response_model=Chunk)
async def get_chunk(document_id: str, chunk_id: str) -> Chunk:
    try:
        return DocumentService().get_chunk(document_id, chunk_id)
    except ChunkNotFoundError:
        raise HTTPException(status_code=404, detail="Chunk not found")


@router.get("/{document_id}/relations", response_model=list[Relation])
async def list_chunk_relations(document_id: str) -> list[Relation]:
    return DocumentService().list_chunk_relations(document_id)


@router.get("/{document_id}/entities", response_model=list[Entity])
async def list_entities(document_id: str) -> list[Entity]:
    return DocumentService().list_entities(document_id)


@router.get("/{document_id}/entity-relations", response_model=list[EntityRelation])
async def list_entity_relations(document_id: str) -> list[EntityRelation]:
    return DocumentService().list_entity_relations(document_id)


@router.post("/{document_id}/relations", response_model=RelationsBuildResponse)
async def rebuild_relations(document_id: str) -> RelationsBuildResponse:
    from app.tasks.relations import build_document_relations

    try:
        DocumentService().get_document(document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")

    task = build_document_relations.delay(document_id)
    return RelationsBuildResponse(
        document_id=document_id,
        task_id=task.id,
        status="building",
    )
