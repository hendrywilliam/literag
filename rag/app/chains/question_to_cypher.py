from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.chains.base import Chain
from app.services.llm import get_llm


class CypherQuery(BaseModel):
    query: str = Field(description="A read-only Cypher query.")


_SYSTEM_PROMPT = (
    "Translate the user's question into a single read-only Cypher query for a "
    "Neo4j knowledge graph. Return only the Cypher query, no explanation."
)


class QuestionToCypher(Chain[str, str]):
    """Translate a natural-language question into a read-only Cypher query.

    Execution is intentionally out of scope here: this chain only produces the
    query string. Combine it with a graph executor (and `VectorRetrieval`) at a
    later fan-in step.
    """

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self._llm = llm

    def _get_llm(self) -> BaseChatModel:
        return self._llm or get_llm()

    def run(self, input: str) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [("system", _SYSTEM_PROMPT), ("human", "{question}")]
        )
        chain = prompt | self._get_llm().with_structured_output(CypherQuery)
        return chain.invoke({"question": input}).query


_question_to_cypher: QuestionToCypher | None = None


def get_question_to_cypher() -> QuestionToCypher:
    global _question_to_cypher
    if _question_to_cypher is None:
        _question_to_cypher = QuestionToCypher()
    return _question_to_cypher
