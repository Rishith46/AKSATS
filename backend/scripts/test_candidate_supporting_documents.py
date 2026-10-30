import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models.access import User
from app.models.candidates import Candidate, CandidateDocument
from app.models.system import ActivityLog
from app.routers.documents import (
    MAX_BYTES,
    SUPPORTING_DOCUMENT_SLOTS,
    delete_supporting_document,
    upload_supporting_document,
)


def pdf_upload(name: str, data: bytes = b"%PDF-1.7\nsample document") -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(data))


def expect_http_error(status_code: int, callback) -> None:
    try:
        callback()
    except HTTPException as error:
        assert error.status_code == status_code, error.detail
    else:
        raise AssertionError(f"Expected HTTP {status_code}")


def main() -> None:
    assert len(SUPPORTING_DOCUMENT_SLOTS) == 5
    with tempfile.TemporaryDirectory(prefix="aks-supporting-docs-") as directory:
        storage = Path(directory)
        with SessionLocal() as db:
            user = db.scalar(select(User).limit(1))
            if user is None:
                raise RuntimeError("The test requires at least one seeded user")

            candidate = Candidate(full_name="TEST Supporting Documents", recruiter_id=user.id)
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
            candidate_id = candidate.id
            try:
                with patch("app.routers.documents.settings.storage_dir", storage):
                    created = []
                    for index, slot in enumerate(SUPPORTING_DOCUMENT_SLOTS):
                        custom_name = f"Recruiter document {index + 1}" if slot.startswith("other_") else None
                        document = upload_supporting_document(
                            candidate_id,
                            pdf_upload(f"{slot}.pdf", f"%PDF-1.7\n{slot}".encode()),
                            slot,
                            custom_name,
                            db,
                            user,
                        )
                        assert document.slot == slot
                        assert document.mime_type == "application/pdf"
                        created.append(document)

                    assert len(db.scalars(select(CandidateDocument).where(
                        CandidateDocument.candidate_id == candidate_id,
                        CandidateDocument.slot.is_not(None),
                    )).all()) == 5

                    previous = next(document for document in created if document.slot == "other_1")
                    previous_path = storage / previous.storage_path
                    replacement = upload_supporting_document(
                        candidate_id,
                        pdf_upload("updated.pdf", b"%PDF-1.7\nreplacement"),
                        "other_1",
                        "Background check",
                        db,
                        user,
                    )
                    assert replacement.id == previous.id
                    assert replacement.display_name == "Background check"
                    assert not previous_path.exists()
                    assert len(db.scalars(select(CandidateDocument).where(
                        CandidateDocument.candidate_id == candidate_id,
                        CandidateDocument.slot.is_not(None),
                    )).all()) == 5

                    expect_http_error(400, lambda: upload_supporting_document(
                        candidate_id, pdf_upload("license.png"), "drivers_license", None, db, user))
                    expect_http_error(400, lambda: upload_supporting_document(
                        candidate_id, pdf_upload("invalid.pdf", b"not a pdf"), "visa", None, db, user))
                    expect_http_error(400, lambda: upload_supporting_document(
                        candidate_id, pdf_upload("sixth.pdf"), "other_4", "Extra", db, user))
                    expect_http_error(422, lambda: upload_supporting_document(
                        candidate_id, pdf_upload("unnamed.pdf"), "other_2", "  ", db, user))
                    expect_http_error(422, lambda: upload_supporting_document(
                        candidate_id, pdf_upload("long-name.pdf"), "other_2", "x" * 101, db, user))
                    expect_http_error(413, lambda: upload_supporting_document(
                        candidate_id,
                        pdf_upload("oversized.pdf", b"%PDF-" + b"x" * MAX_BYTES),
                        "other_2",
                        "Oversized",
                        db,
                        user,
                    ))
                    expect_http_error(409, lambda: upload_supporting_document(
                        candidate_id,
                        pdf_upload("duplicate.pdf", f"%PDF-1.7\n{created[0].slot}".encode()),
                        "other_2",
                        "Duplicate",
                        db,
                        user,
                    ))

                    delete_supporting_document(candidate_id, replacement.id, db, user)
                    assert db.get(CandidateDocument, replacement.id) is None

                    expect_http_error(404, lambda: delete_supporting_document(
                        candidate_id, -1, db, user))
            finally:
                docs = db.scalars(select(CandidateDocument).where(
                    CandidateDocument.candidate_id == candidate_id)).all()
                for document in docs:
                    (storage / document.storage_path).unlink(missing_ok=True)
                db.execute(delete(ActivityLog).where(
                    ActivityLog.object_type == "candidate",
                    ActivityLog.object_id == candidate_id,
                ))
                db.execute(delete(Candidate).where(Candidate.id == candidate_id))
                db.commit()

    print("Candidate supporting document slot and PDF validation checks passed.")


if __name__ == "__main__":
    main()
