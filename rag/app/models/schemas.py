from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    document_id: str
    source: str
    chunk_count: int


class DocumentDetail(BaseModel):
    document_id: str
    source: str
    chunk_count: int


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    source: str
    text: str


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = Field(default=None, ge=1, le=100)


class QuerySource(BaseModel):
    chunk_id: str
    document_id: str
    source: str
    score: float
    text: str


class QueryResponse(BaseModel):
    question: str
    sources: list[QuerySource]
