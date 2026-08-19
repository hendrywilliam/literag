import hashlib
from hashlib import sha256
import secrets
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import (
    Chunk,
    DocumentDetail,
    DocumentSummary,
    UploadResponse,
)
from app.services.document_service import (
    ChunkNotFoundError,
    DocumentNotFoundError,
    DocumentService,
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
