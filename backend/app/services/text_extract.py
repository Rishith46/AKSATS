import logging
from pathlib import Path

log = logging.getLogger("aks_ats.extract")


class ExtractionError(Exception):
    pass


def extract_text(path: Path) -> str:
    """Return plain text from a pdf or docx file. Raises ExtractionError if it cannot."""
    ext = path.suffix.lower().lstrip(".")
    try:
        if ext == "pdf":
            from pdfminer.high_level import extract_text as pdf_text
            text = pdf_text(str(path))
        elif ext == "docx":
            import docx
            d = docx.Document(str(path))
            parts = [p.text for p in d.paragraphs]
            for t in d.tables:
                for row in t.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            text = "\n".join(parts)
        elif ext == "doc":
            raise ExtractionError("Old .doc format is not supported; needs review")
        else:
            raise ExtractionError(f"Unsupported file type: {ext}")
    except ExtractionError:
        raise
    except Exception as exc:
        log.exception("Text extraction failed for %s", path.name)
        raise ExtractionError(f"Could not read file: {exc}") from exc

    text = (text or "").strip()
    if len(text) < 50:
        raise ExtractionError("Very little text found (possibly a scanned image); needs review")
    return text