from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Chain(ABC, Generic[InputT, OutputT]):
    """Minimal chain abstraction for composing retrieval/QA steps.

    Concrete chains implement `run(input)`. This follows the codebase's
    lightweight style (like `app/loaders/BaseLoader`) rather than LangChain LCEL.
    """

    @abstractmethod
    def run(self, input: InputT) -> OutputT:
        raise NotImplementedError
