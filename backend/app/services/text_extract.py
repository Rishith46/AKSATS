import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table

log = logging.getLogger("aks_ats.extract")


class ExtractionError(Exception):
    pass


def _docx_text(parent) -> list[str]:
    """Extract paragraph and table text in document order, including nested tables."""
    parts = []
    if hasattr(parent, "element") and hasattr(parent.element, "body"):
        container = parent.element.body
    elif hasattr(parent, "_tc"):
        container = parent._tc
    else:
        container = parent._element

    for child in container.iterchildren():
        if isinstance(child, CT_P):
            tokens = []
            for node in child.iter():
                tag = node.tag.rsplit("}", 1)[-1]
                if tag == "t" and node.text:
                    tokens.append(node.text)
                elif tag in {"br", "cr"}:
                    tokens.append("\n")
                elif tag == "tab":
                    tokens.append("\t")
            value = "".join(tokens).strip()
            if value:
                parts.append(value)
        elif isinstance(child, CT_Tbl):
            table = Table(child, parent)
            for row in table.rows:
                for cell in row.cells:
                    parts.extend(_docx_text(cell))
    return parts


def _extract_docx(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    parts = _docx_text(document)
    for section in document.sections:
        for part in (section.header, section.first_page_header, section.even_page_header,
                     section.footer, section.first_page_footer, section.even_page_footer):
            parts.extend(_docx_text(part))
    return "\n".join(parts)


def _extract_doc(path: Path) -> str:
    failures = []
    if os.name == "nt":
        powershell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if powershell:
            script = r"""
$ErrorActionPreference = 'Stop'
$word = $null
$document = $null
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $document = $word.Documents.Open($env:AKS_DOC_PATH, $false, $true, $false)
    [Console]::Out.Write($document.Content.Text)
} finally {
    if ($document -ne $null) { $document.Close(0) }
    if ($word -ne $null) { $word.Quit() }
}
"""
            try:
                result = subprocess.run(
                    [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                    check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=90, env={**os.environ, "AKS_DOC_PATH": str(path.resolve())},
                )
                if result.stdout.strip():
                    return result.stdout.strip()
                failures.append("Microsoft Word returned no text")
            except (OSError, subprocess.SubprocessError) as exc:
                failures.append(f"Microsoft Word conversion failed: {exc}")

    antiword = shutil.which("antiword")
    if antiword:
        try:
            result = subprocess.run(
                [antiword, str(path)], check=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60,
            )
            if result.stdout.strip():
                return result.stdout.strip()
            failures.append("antiword returned no text")
        except (OSError, subprocess.SubprocessError) as exc:
            failures.append(f"antiword conversion failed: {exc}")

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        try:
            with tempfile.TemporaryDirectory(prefix="aks-doc-") as temp_dir:
                subprocess.run(
                    [soffice, "--headless", "--convert-to", "txt:Text", "--outdir", temp_dir, str(path)],
                    check=True, capture_output=True, timeout=90,
                )
                converted = Path(temp_dir) / f"{path.stem}.txt"
                if converted.is_file():
                    text = converted.read_text(encoding="utf-8", errors="replace").strip()
                    if text:
                        return text
                failures.append("LibreOffice returned no text")
        except (OSError, subprocess.SubprocessError) as exc:
            failures.append(f"LibreOffice conversion failed: {exc}")

    reason = "Legacy .doc needs Microsoft Word, LibreOffice, or antiword installed"
    if failures:
        reason += "; " + "; ".join(failures)
    raise ExtractionError(reason)


def extract_text(path: Path) -> str:
    """Return document text from PDF, DOCX, or legacy DOC files."""
    ext = path.suffix.lower().lstrip(".")
    try:
        if ext == "pdf":
            from pdfminer.high_level import extract_text as pdf_text
            text = pdf_text(str(path))
        elif ext == "docx":
            text = _extract_docx(path)
        elif ext == "doc":
            text = _extract_doc(path)
        else:
            raise ExtractionError(f"Unsupported file type: {ext}")
    except ExtractionError:
        raise
    except Exception as exc:
        log.exception("Text extraction failed for %s", path.name)
        raise ExtractionError(f"Could not read file: {exc}") from exc

    text = (text or "").strip()
    if not text:
        reason = "No text found (PDF may be scanned and require OCR)" if ext == "pdf" \
            else "No text found in document"
        raise ExtractionError(reason)
    return text