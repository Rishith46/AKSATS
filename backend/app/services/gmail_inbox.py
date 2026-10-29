import base64
import hashlib
import json
import logging
import re
import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.system import GmailScannedMessage, ResumeIngestion

log = logging.getLogger("aks_ats.gmail")

MAX_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
MIME_EXTENSIONS = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
RESUME_CONTEXT_RE = re.compile(
    r"\b(application|applied|applicant|candidate|job application)\b",
    re.I,
)
RESUME_FILENAME_RE = re.compile(
    r"(?:^|[\s._-])(resume|résumé|cv|curriculum(?:[\s._-]+vitae)?)(?:$|[\s._-])",
    re.I,
)
RESUME_HEADING_RE = re.compile(
    r"\b(experience|employment history|work history|education|professional summary|"
    r"skills|certifications)\b",
    re.I,
)
DATE_RANGE_RE = re.compile(
    r"\b(?:19|20)\d{2}\s*(?:-|–|—|to)\s*(?:(?:19|20)\d{2}|present|current)\b",
    re.I,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)


class GmailInboxError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(settings.gmail_client_id and settings.gmail_client_secret
                and settings.gmail_refresh_token)



def _request_json(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict | None = None,
) -> dict:
    request = Request(
        url,
        data=data,
        headers=headers or {},
        method="POST" if data else "GET",
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read())

    except HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
            error_code = error_body.get("error", "unknown")
            description = error_body.get(
                "error_description", "No description provided"
            )
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            error_code = "unknown"
            description = "Google returned an unreadable error response"

        log.error(
            "OAuth/Gmail request failed: HTTP %s; error=%s; description=%s",
            exc.code,
            error_code,
            description,
        )

        raise GmailInboxError(
            f"Gmail API request failed (HTTP {exc.code})"
        ) from exc

    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise GmailInboxError("Gmail API request failed") from exc


def _access_token() -> str:
    values = urlencode({
        "client_id": settings.gmail_client_id,
        "client_secret": settings.gmail_client_secret,
        "refresh_token": settings.gmail_refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    result = _request_json(
        "https://oauth2.googleapis.com/token",
        data=values,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise GmailInboxError("Google did not return an access token")
    return token


def _gmail_json(token: str, path: str, query: dict | None = None) -> dict:
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/{path}"
    if query:
        url += "?" + urlencode(query)
    return _request_json(url, headers={"Authorization": f"Bearer {token}"})


def _walk_parts(part: dict):
    if part.get("filename") or part.get("body", {}).get("attachmentId"):
        yield part
    for child in part.get("parts", []):
        yield from _walk_parts(child)


def _decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _attachment_bytes(token: str, message_id: str, part: dict) -> bytes:
    body = part.get("body") or {}
    if body.get("data"):
        return _decode(body["data"])
    attachment_id = body.get("attachmentId")
    if not attachment_id:
        return b""
    response = _gmail_json(
        token, f"messages/{message_id}/attachments/{attachment_id}")
    encoded = response.get("data")
    return _decode(encoded) if encoded else b""


def _extension(part: dict, data: bytes) -> str | None:
    filename_ext = Path(Path(part.get("filename") or "").name).suffix.lower().lstrip(".")
    mime = (part.get("mimeType") or "").lower()
    ext = filename_ext if filename_ext in ALLOWED_EXTENSIONS else MIME_EXTENSIONS.get(mime)
    if ext == "pdf" and data.startswith(b"%PDF-"):
        return ext
    if ext == "doc" and data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return ext
    if ext == "docx" and zipfile.is_zipfile(BytesIO(data)):
        try:
            with zipfile.ZipFile(BytesIO(data)) as archive:
                if "[Content_Types].xml" in archive.namelist() and "word/document.xml" in archive.namelist():
                    return ext
        except (OSError, zipfile.BadZipFile):
            return None
    return None


def _is_resume(text: str, filename: str, context: str) -> bool:
    if RESUME_FILENAME_RE.search(filename):
        return True
    if not text.strip():
        return False
    has_contact = bool(EMAIL_RE.search(text)) or bool(re.search(r"\+?\d[\d ().-]{7,}\d", text))
    has_heading = bool(RESUME_HEADING_RE.search(text))
    dated_roles = len(DATE_RANGE_RE.findall(text)) >= 2
    content_signals = sum((has_contact, has_heading, dated_roles))
    if content_signals >= 2:
        return True
    return bool(RESUME_CONTEXT_RE.search(context)) and (
        has_contact or has_heading or dated_roles
    )


def _message_context(message: dict) -> str:
    bits = [message.get("snippet", "")]
    payload = message.get("payload") or {}
    for header in payload.get("headers", []):
        if header.get("name", "").lower() == "subject":
            bits.append(header.get("value", ""))
    return " ".join(bits)


def _resume_parts(payload: dict):
    for part in _walk_parts(payload):
        filename = Path(part.get("filename") or "").name
        if filename:
            yield filename, part


def _email_key(message_id: str, part: dict, data: bytes) -> str:
    attachment_id = (part.get("body") or {}).get("attachmentId")
    key_part = attachment_id or hashlib.sha256(data).hexdigest()
    return f"{message_id}:{key_part}"


def _stage_attachment(db: Session, message_id: str, filename: str,
                      part: dict, data: bytes, ext: str) -> bool:
    email_key = _email_key(message_id, part, data)
    if db.scalar(select(ResumeIngestion.id).where(
            ResumeIngestion.email_message_id == email_key)) is not None:
        return False

    normalized_name = filename
    if Path(filename).suffix.lower() != f".{ext}":
        normalized_name = f"{Path(filename).stem or 'resume'}.{ext}"

    rel = f"inbox/{uuid.uuid4().hex}.{ext}"
    path = settings.storage_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    row = ResumeIngestion(
        source="email", email_message_id=email_key, original_filename=normalized_name[:500],
        staged_path=rel, status="Received",
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        # A concurrent worker may have stored this attachment first.
        if db.scalar(select(ResumeIngestion.id).where(
                ResumeIngestion.email_message_id == email_key)) is not None:
            return False
        raise
    log.info("Queued Gmail resume attachment as inbox row %s", row.id)
    return True


def poll_gmail(db: Session) -> int:
    """Fetch recent Gmail attachments and enqueue confirmed resumes for the standard worker."""
    if not is_configured():
        return 0
    token = _access_token()
    query = {
        "q": f"in:inbox has:attachment newer_than:{max(1, settings.gmail_lookback_days)}d",
        "maxResults": 100,
    }
    page_token = None
    queued = 0
    pages = 0
    while pages < 5:
        if page_token:
            query["pageToken"] = page_token
        response = _gmail_json(token, "messages", query)
        for item in response.get("messages", []):
            message_id = item.get("id")
            if not message_id:
                continue
            if db.scalar(select(GmailScannedMessage.id).where(
                    GmailScannedMessage.gmail_message_id == message_id)) is not None:
                continue
            message = _gmail_json(token, f"messages/{message_id}", {"format": "full"})
            payload = message.get("payload") or {}
            context = _message_context(message)
            for filename, part in _resume_parts(payload):
                if (part.get("body") or {}).get("size", 0) > MAX_BYTES:
                    continue
                data = _attachment_bytes(token, message_id, part)
                if not data or len(data) > MAX_BYTES:
                    continue
                key = _email_key(message_id, part, data)
                if db.scalar(select(ResumeIngestion.id).where(
                        ResumeIngestion.email_message_id == key)) is not None:
                    continue
                ext = _extension(part, data)
                if ext is None:
                    continue
                text = extract_text_from_bytes(filename, ext, data)
                if not _is_resume(text, filename, context):
                    continue
                if _stage_attachment(db, message_id, filename, part, data, ext):
                    queued += 1
            db.add(GmailScannedMessage(gmail_message_id=message_id))
            db.commit()
        pages += 1
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return queued


def extract_text_from_bytes(filename: str, extension: str, data: bytes) -> str:
    """Use the existing extractor via a private temporary file to classify attachments."""
    import tempfile

    from app.services.text_extract import ExtractionError, extract_text

    with tempfile.TemporaryDirectory(prefix="aks-gmail-check-") as directory:
        path = Path(directory) / f"resume.{extension}"
        path.write_bytes(data)
        try:
            return extract_text(path)
        except (ExtractionError, OSError):
            log.warning("Could not inspect Gmail attachment text; it was not imported")
            return ""
