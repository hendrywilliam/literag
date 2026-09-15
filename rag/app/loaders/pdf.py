from io import BytesIO

from pypdf import PdfReader

from app.loaders.base import BaseLoader


class PdfLoader(BaseLoader):
    """Loads PDF files, extracting text from every page."""

    def load(self, data: bytes) -> str:
        reader = PdfReader(BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()

    @classmethod
    def detect(cls, data: bytes) -> bool:
        return data.startswith(b"%PDF")
