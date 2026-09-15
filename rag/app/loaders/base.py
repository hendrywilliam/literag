from abc import ABC, abstractmethod


class BaseLoader(ABC):
    """Abstract base for document loaders.

    Each loader extracts plain text from raw file bytes. Subclasses also
    declare `detect()` so the registry can pick the right loader from the
    file's magic bytes (content), not its extension.
    """

    @abstractmethod
    def load(self, data: bytes) -> str:
        """Extract text from raw file bytes."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def detect(cls, data: bytes) -> bool:
        """Return True if this loader can handle the given bytes."""
        raise NotImplementedError
