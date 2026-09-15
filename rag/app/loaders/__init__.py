import os

from app.loaders.base import BaseLoader
from app.loaders.html import HtmlLoader
from app.loaders.pdf import PdfLoader
from app.loaders.txt import TxtLoader

ALLOWED_EXTENSIONS = frozenset({"pdf", "txt", "html"})

_LOADER_BY_EXTENSION: dict[str, type[BaseLoader]] = {
    "pdf": PdfLoader,
    "html": HtmlLoader,
    "txt": TxtLoader,
}


def extract_extension(filename: str) -> str | None:
    """Extract the file extension safely from a (decoded) filename.

    Handles known bypasses: null bytes and double extensions. The filename is
    never used for storage, so this only determines the loader.
    """
    filename = filename.replace("\x00", "")
    basename = os.path.basename(filename)
    if "." not in basename:
        return None
    ext = basename.rsplit(".", 1)[-1].strip().lower()
    return ext or None


def loader_for_extension(ext: str) -> type[BaseLoader] | None:
    return _LOADER_BY_EXTENSION.get(ext)


def get_loader(data: bytes) -> BaseLoader:
    """Return the loader matching the file's magic bytes (content)."""
    for loader_cls in (PdfLoader, HtmlLoader, TxtLoader):
        if loader_cls.detect(data):
            return loader_cls()
    return TxtLoader()


__all__ = [
    "BaseLoader",
    "TxtLoader",
    "PdfLoader",
    "HtmlLoader",
    "ALLOWED_EXTENSIONS",
    "extract_extension",
    "loader_for_extension",
    "get_loader",
]
