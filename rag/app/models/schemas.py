from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    document_id: str
    source: str
    chunk_count: int
    status: str = "indexed"


class DocumentDetail(BaseModel):
    document_id: str
    source: str
    chunk_count: int
    status: str = "indexed"


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    source: str
    text: str
    chunk_index: int = 0


class Relation(BaseModel):
    source_chunk_id: str
    target_chunk_id: str
    relation_type: str
    description: str = ""


class Entity(BaseModel):
    id: str
    type: str
    properties: dict = {}


class EntityRelation(BaseModel):
    source_id: str
    source_type: str
    relation_type: str
    target_id: str
    target_type: str


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


class RelationsBuildResponse(BaseModel):
    document_id: str
    task_id: str
    status: str


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
