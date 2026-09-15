from app.loaders.base import BaseLoader


class TxtLoader(BaseLoader):
    """Loads plain text files. Fallback loader for any non-PDF/non-HTML bytes."""

    def load(self, data: bytes) -> str:
        return data.decode("utf-8")

    @classmethod
    def detect(cls, data: bytes) -> bool:
        return True
