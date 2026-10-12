import hashlib
import logging
import mimetypes
import shutil
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.candidates import Candidate, CandidateDocument
from app.models.system import ActivityLog, ResumeIngestion
from app.services.duplicates import find_by_hash, find_matches, record_pair
from app.services.parse_pipeline import parse_document

log = logging.getLogger("aks_ats.process_inbox")


def _now():
    return datetime.now(timezone.utc)


def _fail(db: Session, ingestion_id: int, status: str, reason: str) -> None:
    row = db.get(ResumeIngestion, ingestion_id)
    row.status = status
    row.issues = {"reason": reason}
    row.processed_at = _now()
    db.commit()


def process_ingestion(db: Session, ingestion_id: int, user_id: int | None = None) -> dict:
    row = db.get(ResumeIngestion, ingestion_id)
    if not row:
        raise ValueError("Inbox row not found")
    if row.status != "Received":
        raise ValueError(f"Row is '{row.status}'; only 'Received' rows can be processed")

    src = settings.storage_dir / row.staged_path if row.staged_path else None
    if src is None or not src.is_file():
        _fail(db, ingestion_id, "Failed", "Staged file is missing")
        return {"status": "Failed", "reason": "Staged file is missing"}

    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    same = find_by_hash(db, sha)
    if same:
        row.status = "Duplicate"
        row.duplicate_of_candidate_id = same
        row.issues = {"reason": "Identical file already stored", "signals": ["file_hash"]}
        row.processed_at = _now()
        db.add(ActivityLog(user_id=user_id, action="inbox.duplicate", object_type="candidate",
                           object_id=same, new_value={"ingestion_id": ingestion_id,
                                                      "signals": ["file_hash"]}))
        db.commit()
        return {"status": "Duplicate", "duplicate_of": same, "signals": ["file_hash"]}

    row.status = "Processing"
    db.commit()

    dest = None
    try:
        data = src.read_bytes()
        ext = src.suffix.lower().lstrip(".")
        cand = Candidate()
        db.add(cand)
        db.flush()
        rel = f"candidates/{cand.id}/{uuid.uuid4().hex}.{ext}"
        dest = settings.storage_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        doc = CandidateDocument(
            candidate_id=cand.id, kind="resume", original_filename=row.original_filename,
            storage_path=rel, mime_type=mimetypes.guess_type(row.original_filename)[0],
            size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
            version_no=1, is_current=True, uploaded_by=user_id)
        db.add(doc)
        db.flush()
        cand_id, doc_id = cand.id, doc.id
        row.candidate_id = cand_id
        row.document_id = doc_id
        db.add(ActivityLog(user_id=user_id, action="candidate.created", object_type="candidate",
                           object_id=cand_id,
                           new_value={"source": "inbox", "ingestion_id": ingestion_id}))
        db.commit()
    except Exception:
        db.rollback()
        if dest is not None and dest.exists() and not src.exists():
            shutil.move(str(dest), str(src))
        log.exception("Could not create candidate from inbox row %s", ingestion_id)
        _fail(db, ingestion_id, "Failed", "Could not create candidate; see server log")
        raise

    try:
        result = parse_document(db, doc_id, user_id)
    except Exception:
        db.rollback()
        log.exception("Parsing failed for inbox row %s", ingestion_id)
        _fail(db, ingestion_id, "Needs Review", "Parsing failed; see server log")
        return {"status": "Needs Review", "candidate_id": cand_id, "reason": "Parsing failed"}

    row = db.get(ResumeIngestion, ingestion_id)
    matches = find_matches(db, db.get(Candidate, cand_id))
    if matches:
        for other, sig in matches.items():
            record_pair(db, cand_id, other, sig)
        first = min(matches)
        db.get(Candidate, cand_id).parse_status = "Possible Duplicate - Review Required"
        row.status = "Duplicate"
        row.duplicate_of_candidate_id = first
        row.issues = {"reason": "Possible duplicate - review required",
                      "matches": {str(k): v for k, v in matches.items()}}
        row.processed_at = _now()
        db.add(ActivityLog(user_id=user_id, action="inbox.duplicate", object_type="candidate",
                           object_id=cand_id, new_value={"ingestion_id": ingestion_id,
                                                         "matches": {str(k): v for k, v in matches.items()}}))
        db.commit()
        return {"status": "Duplicate", "candidate_id": cand_id, "duplicate_of": first,
                "matches": matches}
    if result["status"] == "Parsed":
        row.status = "Processed"
        row.issues = None
    else:
        row.status = "Needs Review"
        reason = result.get("reason") or ("Missing: " + ", ".join(result.get("missing", [])))
        row.issues = {"reason": reason}
    row.processed_at = _now()
    db.commit()
    return {"status": row.status, "candidate_id": cand_id, "document_id": doc_id,
            "parse": result}