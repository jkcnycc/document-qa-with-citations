"""Document loading.

Sections carry their own location label (a heading, or a PDF page number) so a
citation can point somewhere a human can actually check, rather than at an
opaque chunk id.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Section:
    source: str    # file name, e.g. "refund-policy.md"
    location: str  # "Standard refunds" or "page 3"
    text: str


class UnsupportedDocumentError(RuntimeError):
    pass


_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _load_markdown(path: Path) -> List[Section]:
    """Split on headings so citations name a section a reader can find."""
    sections: List[Section] = []
    current_heading = ""
    buffer: List[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            sections.append(
                Section(source=path.name, location=current_heading or "(intro)", text=body)
            )

    for line in path.read_text(encoding="utf-8").splitlines():
        match = _MD_HEADING_RE.match(line)
        if match:
            flush()
            buffer = []
            current_heading = match.group(2).strip()
        else:
            buffer.append(line)
    flush()

    return sections


def _load_text(path: Path) -> List[Section]:
    body = path.read_text(encoding="utf-8").strip()
    return [Section(source=path.name, location="(whole file)", text=body)] if body else []


def _load_pdf(path: Path) -> List[Section]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise UnsupportedDocumentError(
            f"Reading {path.name} needs pypdf. Install it with: pip install pypdf"
        ) from exc

    sections: List[Section] = []
    reader = PdfReader(str(path))
    for page_number, page in enumerate(reader.pages, start=1):
        body = (page.extract_text() or "").strip()
        if body:
            sections.append(
                Section(source=path.name, location=f"page {page_number}", text=body)
            )
    return sections


_LOADERS = {
    ".md": _load_markdown,
    ".markdown": _load_markdown,
    ".txt": _load_text,
    ".pdf": _load_pdf,
}


def load_sections(directory: str | Path, extensions: Iterable[str]) -> List[Section]:
    """Read every supported file in a directory into Sections."""
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"Document directory not found: {root}")

    allowed = {ext.lower() for ext in extensions}
    sections: List[Section] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        loader = _LOADERS.get(path.suffix.lower())
        if loader is None:
            log.warning("no loader for %s, skipping", path.name)
            continue
        found = loader(path)
        log.info("loaded %s: %d section(s)", path.name, len(found))
        sections.extend(found)

    if not sections:
        raise FileNotFoundError(
            f"No readable documents found in {root} (looked for {sorted(allowed)})"
        )

    return sections
