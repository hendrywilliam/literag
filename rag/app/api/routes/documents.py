import hashlib
from hashlib import sha256
import secrets
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.loaders import (
    ALLOWED_EXTENSIONS,
    PdfLoader,
    extract_extension,
    loader_for_extension,
)
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
from app.services.graph_store import (
    ChunkNotFoundError,
    DocumentNotFoundError,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    settings = get_settings()

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = extract_extension(file.filename)
    if ext is None or ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type. Allowed extensions: "
                f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    data = await file.read(settings.max_upload_size + 1)
    if len(data) > settings.max_upload_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size} bytes",
        )

    loader_cls = loader_for_extension(ext)
    loader = loader_cls()

    if ext == "pdf" and not PdfLoader.detect(data):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")

    try:
        content = loader.load(data)
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File is not valid text (unsupported binary format)",
        )

    if not content.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    rand = secrets.token_bytes(16)
    hash = hashlib.sha256(rand)
    fileName = hash.hexdigest()

    service = DocumentService()
    document_id, chunk_count = service.upload_text(content, fileName)

    if settings.relation_enabled:
        from app.tasks.relations import build_document_relations

        build_document_relations.delay(document_id)

    return UploadResponse(
        document_id=document_id,
        filename=fileName,
        chunk_count=chunk_count,
    )


@router.get("", response_model=list[DocumentSummary])
async def list_documents() -> list[DocumentSummary]:
    documents = DocumentService().list_documents()
    return [DocumentSummary(**doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: str) -> DocumentDetail:
    try:
        doc = DocumentService().get_document(document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetail(**doc)


@router.get("/{document_id}/chunks", response_model=list[Chunk])
async def list_chunks(document_id: str) -> list[Chunk]:
    try:
        chunks = DocumentService().list_chunks(document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    return [Chunk(**chunk) for chunk in chunks]


@router.get("/{document_id}/chunks/{chunk_id}", response_model=Chunk)
async def get_chunk(document_id: str, chunk_id: str) -> Chunk:
    try:
        chunk = DocumentService().get_chunk(document_id, chunk_id)
    except ChunkNotFoundError:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return Chunk(**chunk)


@router.get("/{document_id}/relations", response_model=list[Relation])
async def list_chunk_relations(document_id: str) -> list[Relation]:
    relations = DocumentService().list_chunk_relations(document_id)
    return [Relation(**relation) for relation in relations]


@router.get("/{document_id}/entities", response_model=list[Entity])
async def list_entities(document_id: str) -> list[Entity]:
    entities = DocumentService().list_entities(document_id)
    return [Entity(**entity) for entity in entities]


@router.get("/{document_id}/entity-relations", response_model=list[EntityRelation])
async def list_entity_relations(document_id: str) -> list[EntityRelation]:
    relations = DocumentService().list_entity_relations(document_id)
    return [EntityRelation(**relation) for relation in relations]


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
