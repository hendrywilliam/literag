from html.parser import HTMLParser

from app.loaders.base import BaseLoader

class _TextExtractor(HTMLParser):
    _SKIP_TAGS = {"script", "style", "noscript", "head", "template"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        return "\n".join(self._parts)


class HtmlLoader(BaseLoader):
    """Loads HTML files, extracting visible text (scripts/styles stripped)."""

    def load(self, data: bytes) -> str:
        parser = _TextExtractor()
        parser.feed(data.decode("utf-8", errors="replace"))
        return parser.text()

    @classmethod
    def detect(cls, data: bytes) -> bool:
        sample = data[:4096].lstrip().lower()
        return sample.startswith(b"<!doctype html") or b"<html" in sample
