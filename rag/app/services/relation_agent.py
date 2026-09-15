from typing import Any

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import LLMGraphTransformer
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.graph_store import get_graph_store, sanitize_label
from app.services.llm import get_llm
from app.services.vector_store import get_vector_store

RELATION_TYPES = ["CONTINUES", "ELABORATES", "CONTRASTS", "REFERENCES", "SUPPORTS"]


class ChunkRelationDecision(BaseModel):
    relation_type: str = Field(
        description=f"One of {RELATION_TYPES} or 'NONE' if unrelated."
    )
    description: str = Field(description="Short justification of the relation.")


def _sanitize_properties(properties: dict) -> dict:
    cleaned: dict = {}
    for key, value in properties.items():
        cleaned[key] = _sanitize_value(value)
    return cleaned


def _sanitize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(v) for v in value]
    return str(value)


class RelationAgent:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._graph_store = get_graph_store()
        self._vector_store = get_vector_store()
        self._llm = get_llm()

    def _chunks_to_documents(self, chunks: list[Any]) -> list[Document]:
        documents = []
        for chunk in chunks:
            doc = Document(
                page_content=chunk.text,
                metadata={
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                },
            )
            doc.id = chunk.chunk_id
            documents.append(doc)
        return documents

    def _extract_entities(
        self, documents: list[Document]
    ) -> tuple[list[dict], list[dict], dict[str, list[str]]]:
        transformer = LLMGraphTransformer(
            llm=self._llm,
            node_properties=True,
            relationship_properties=True,
        )

        node_map: dict[tuple[str, str], dict] = {}
        relationship_map: dict[tuple[str, str, str], dict] = {}
        chunk_entities: dict[str, list[str]] = {}

        for doc in documents:
            graph_doc = transformer.process_response(doc)
            chunk_id = doc.id or doc.metadata.get("chunk_id", "")
            entity_ids: list[str] = []

            for node in graph_doc.nodes:
                label = sanitize_label(node.type)
                key = (str(node.id), label)
                if key not in node_map:
                    node_map[key] = {
                        "id": str(node.id),
                        "label": label,
                        "properties": _sanitize_properties(dict(node.properties)),
                    }
                entity_ids.append(str(node.id))

            if chunk_id and entity_ids:
                chunk_entities[chunk_id] = list(dict.fromkeys(entity_ids))

            for rel in graph_doc.relationships:
                rel_type = sanitize_label(rel.type).upper() or "RELATED_TO"
                key = (str(rel.source.id), rel_type, str(rel.target.id))
                if key not in relationship_map:
                    relationship_map[key] = {
                        "source": str(rel.source.id),
                        "target": str(rel.target.id),
                        "type": rel_type,
                        "properties": _sanitize_properties(dict(rel.properties)),
                    }

        return list(node_map.values()), list(relationship_map.values()), chunk_entities

    def _classify_relation(self, source_text: str, target_text: str) -> ChunkRelationDecision | None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You classify the relationship between two text chunks from the "
                    "same document. Choose exactly one of: "
                    + ", ".join(RELATION_TYPES)
                    + ", or 'NONE' if the chunks are unrelated. "
                    "Be conservative; prefer NONE when in doubt.",
                ),
                (
                    "human",
                    "Chunk A:\n{source}\n\nChunk B:\n{target}",
                ),
            ]
        )
        chain = prompt | self._llm.with_structured_output(ChunkRelationDecision)
        return chain.invoke({"source": source_text, "target": target_text})

    def build_document_relations(self, document_id: str) -> dict:
        chunks = self._graph_store.list_chunks(document_id)
        if not chunks:
            return {"document_id": document_id, "entities": 0, "entity_relations": 0, "chunk_relations": 0}

        documents = self._chunks_to_documents(chunks)

        nodes, relationships, chunk_entities = self._extract_entities(documents)
        self._graph_store.add_entities(nodes, relationships)
        self._graph_store.link_chunks_to_entities(chunk_entities)

        chunk_by_id = {c.chunk_id: c for c in chunks}
        relations = self._build_chunk_relations(chunks, chunk_by_id)
        self._graph_store.add_chunk_relations(relations)

        return {
            "document_id": document_id,
            "entities": len(nodes),
            "entity_relations": len(relationships),
            "chunk_relations": len(relations),
        }

    def _build_chunk_relations(self, chunks: list[Any], chunk_by_id: dict) -> list[Any]:
        from app.models.schemas import Relation

        k = self._settings.relation_candidates
        relations: list[Relation] = []
        seen_pairs: set[frozenset] = set()

        for chunk in chunks:
            candidates = self._vector_store.similarity_search_with_score(
                chunk.text,
                k=k + 1,
                filter={"document_id": chunk.document_id},
            )
            for doc, _score in candidates:
                other_id = doc.metadata.get("chunk_id", "")
                if other_id == chunk.chunk_id:
                    continue
                if other_id not in chunk_by_id:
                    continue
                pair = frozenset({chunk.chunk_id, other_id})
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                decision = self._classify_relation(
                    chunk.text, chunk_by_id[other_id].text
                )
                if decision is None or decision.relation_type.upper() == "NONE":
                    continue
                if decision.relation_type.upper() not in RELATION_TYPES:
                    continue
                relations.append(
                    Relation(
                        source_chunk_id=chunk.chunk_id,
                        target_chunk_id=other_id,
                        relation_type=decision.relation_type.upper(),
                        description=decision.description,
                    )
                )

        return relations


_agent: RelationAgent | None = None


def get_relation_agent() -> RelationAgent:
    global _agent
    if _agent is None:
        _agent = RelationAgent()
    return _agent
